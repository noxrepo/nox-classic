#include "messenger_core.hh"
#include "component.hh"
#include "buffer.hh"
#include "async_io.hh"
#include <errno.h>
#include "errno_exception.hh"
#include <xercesc/dom/DOM.hpp>
#include "vlog.hh"
#include "assert.hh"

namespace vigil
{
  using namespace vigil::container;    

  static Vlog_module lg("messenger_core");
  static const std::string app_name("messenger_core");
 
  Msg_stream::Msg_stream(Async_stream* stream_):
    stream(stream_), magic(NULL)
  {};
 
  Msg_stream::Msg_stream(Async_stream* stream_, bool isSSL_):
    stream(stream_), isSSL(isSSL_), magic(NULL)
  {};


  Msg_stream::Msg_stream(Msg_stream& stream_):
    magic(NULL)
  {
    stream =stream_.stream;
    isSSL = stream_.isSSL;
  }

  Msg_event::Msg_event(messenger_msg* message, Msg_stream* socket, 
		       ssize_t size):
    Event(static_get_name())
  {
    sock = socket;

    //Allocate memory and copy message
    if (size < sizeof(messenger_msg) && size != 0)
      size = sizeof(messenger_msg);
    len = size;
    raw_msg.reset(new uint8_t[size]);
    memcpy(raw_msg.get(), message, size);
    msg = (messenger_msg*) raw_msg.get();
    VLOG_DBG(lg, "Received packet of length %zu", size);
  }

  Msg_event::~Msg_event()
  {  }

  void Msg_event::dumpBytes()
  {
    uint8_t* readhead =  (uint8_t*) raw_msg.get();
    fprintf(stderr,"messenger_core Msg_event of size %zu\n\t",
	    len);
    for (int i = 0; i < len; i++)
    {
      fprintf(stderr, "%"PRIx8" ", *readhead);
      readhead++;
    }
    fprintf(stderr,"\n");
  }

  void messenger_core::configure(const Configuration* config)
  {
    register_event(Msg_event::static_get_name());
  }
  
  void messenger_core::getInstance(const container::Context* ctxt, 
			      vigil::messenger_core*& scpa) 
  {
    scpa = dynamic_cast<messenger_core*>
      (ctxt->get_by_interface(container::Interface_description
			      (typeid(messenger_core).name())));
  }

  void messenger_core::start_tcp(message_processor* messenger, uint16_t portNo)
  {
    new messenger_server(messenger, portNo);
  }

  void messenger_core::start_ssl(message_processor* messenger, uint16_t portNo, 
				 boost::shared_ptr<Ssl_config>& config)
  {
    new messenger_ssl_server(messenger, portNo, config);
  }

  messenger_server::messenger_server(message_processor* messenger, uint16_t portNo)
  {
    msger = messenger;
    server_sock.set_reuseaddr();
    int error = server_sock.bind(INADDR_ANY, ntohs(portNo));
    if (error)
      throw errno_exception(error, "bind");
    
    error = server_sock.listen(MESSENGER_MAX_CONNECTION);
    if (error)
      throw errno_exception(error, "listen"); 
    
    lg.dbg("messenger TCP interface bound to port %d", portNo);
    start(boost::bind(&messenger_server::run, this));
  }
  
  messenger_server::~messenger_server()
  {
    int error = server_sock.close();
    if (error)
      throw errno_exception(error, "close"); 
  }
  
  void messenger_server::run()
  {
    int error;
    while (true)
    {
      server_sock.accept_wait();
      co_block();
      std::auto_ptr<Tcp_socket> new_socket(server_sock.accept(error, false));
      new messenger_tcp_connection(msger, new_socket);
    }
    if (!error)
      lg.err("messenger TCP accept: %d",error);
  }
  
  messenger_ssl_server::messenger_ssl_server(message_processor* messenger, uint16_t portNo, 
					     boost::shared_ptr<Ssl_config>& config):
    server_sock(config)
  {
    msger = messenger;
    //server_sock.set_reuseaddr();
    int error = server_sock.bind(INADDR_ANY, ntohs(portNo));
    if (error)
      throw errno_exception(error, "bind");
    
    error = server_sock.listen(MESSENGER_MAX_CONNECTION);
    if (error)
      throw errno_exception(error, "listen"); 
    
    lg.dbg("messenger SSL interface bound to port %d", portNo);
    start(boost::bind(&messenger_ssl_server::run, this));
  }
  
  messenger_ssl_server::~messenger_ssl_server()
  {
    int error = server_sock.close();
    if (error)
    throw errno_exception(error, "close"); 
  }
  
  void messenger_ssl_server::run()
  {
    int error;
    while (true)
    {
      server_sock.accept_wait();
      co_block();
      std::auto_ptr<Ssl_socket> new_socket(server_sock.accept(error, false));
      new messenger_ssl_connection(msger, new_socket);
    }
    if (!error)
      lg.err("messenger SSL accept: %d",error);
  }
    
  messenger_tcp_connection::messenger_tcp_connection(message_processor* messenger, 
						     std::auto_ptr<Tcp_socket> new_socket): 
     messenger_connection(messenger), sock(new_socket)
  { 
    msgstream=new Msg_stream(sock.get(), false);
    if (messenger->newConnectionMsg)
      send_new_connection_msg();
    start(boost::bind(&messenger_tcp_connection::run, this));
  }
    
  void messenger_tcp_connection::run()
  {
    Array_buffer buf(MESSENGER_BUFFER_SIZE);
    ssize_t dataSize;
    VLOG_DBG(lg,"TCP socket connection accepted");
    
    running = true;
    currSize = 0;
    while (running)
    {
      //Read message.
      sock->read_wait();
      co_block();
      dataSize = sock->read(buf, false);
      if (dataSize <= 0)
      {
	//Terminating disconnected connection
	post_disconnect();
	running = false;
        break;
      }
      processBlock(buf, dataSize,msgstream);
    }

    int error = sock->close();
    if (error)
      lg.err("messenger TCP connection close with error %d", error);
    lg.dbg("socket closed");
  }

  messenger_ssl_connection::messenger_ssl_connection(message_processor* messenger, 
						     std::auto_ptr<Ssl_socket> new_socket): 
    messenger_connection(messenger), sock(new_socket)
  { 
    msgstream=new Msg_stream(sock.get(), false);
    if (messenger->newConnectionMsg)
      send_new_connection_msg();
    start(boost::bind(&messenger_ssl_connection::run, this));
  }

  void messenger_ssl_connection::run()
  {
    Array_buffer buf(MESSENGER_BUFFER_SIZE);
    ssize_t dataSize;
    VLOG_DBG(lg,"SSL socket connection accepted");
    
    running = true;
    currSize = 0;
    while (running)
    {
      //Read message.
      sock->read_wait();
      co_block();
      dataSize = sock->read(buf, false);
      if (dataSize <= 0)
      {
	//Terminating disconnected connection
	post_disconnect();
	running = false;
        break;
      }
      processBlock(buf, dataSize,msgstream);
    }

    int error = sock->close();
    if (error)
      lg.err("messenger SSL connection close with error %d", error);
    lg.dbg("socket closed");
  }

  messenger_connection::messenger_connection(message_processor* messenger)
  {
    VLOG_DBG(lg, "Starting connection with idleInterval %"PRIx16"",
	     messenger->idleInterval);

    echoMissed = 0;
    lastActiveTime = time(NULL);
    msger = messenger;
    endpointer = &internalrecvbuf[0];

    if (msger->idleInterval != 0)
    {
      timeval tv={msger->idleInterval,0};
      msger->post(boost::bind(&messenger_connection::check_idle, this), tv);
    }
  }

  void messenger_connection::send_new_connection_msg()
  {
    messenger_msg* msgbuf = (messenger_msg*) &internalrecvbuf;
    msgbuf->length = htons(0);
    msgbuf->type = 0;
    process(new Msg_event((messenger_msg*) internalrecvbuf, 
			  msgstream, ntohs(msgbuf->length)));
  }

  void messenger_connection::check_idle()
  {
    VLOG_DBG(lg, "Check idle at interval %"PRIx16"",
	     msger->idleInterval);

    if (time(NULL)-lastActiveTime > msger->idleInterval)
    {
      if (echoMissed >= msger->thresholdEchoMissed)
      {
	VLOG_WARN(lg, "Connection terminated due to idle");
	post_disconnect();
	running = false;
	msgstream->stream->close();
	endpointer = &internalrecvbuf[0];
	currSize=0;
      }
      else
      {
	//Send echo
	echoMissed++;
	msger->send_echo(msgstream->stream);
      }
    }

    if (running && msger->idleInterval != 0)
    {
      timeval tv={msger->idleInterval,0};
      msger->post(boost::bind(&messenger_connection::check_idle, this), tv);
    }
  }

  void messenger_connection::post_disconnect()
  {
    messenger_msg* msgbuf = (messenger_msg*) &internalrecvbuf;
    msgbuf->length = htons(3);
    msgbuf->type = MSG_DISCONNECT;
    process(new Msg_event((messenger_msg*) internalrecvbuf, 
			  msgstream, ntohs(msgbuf->length)));
  }

  void messenger_connection::processBlock(Array_buffer& buf, ssize_t& dataSize, 
					  Msg_stream* sock)
  {
    uint8_t* dataPointer = buf.data();
    ssize_t cpSize;

    if (dataSize > MESSENGER_BUFFER_SIZE)
      VLOG_WARN(lg, "Read buffer insufficient, check MESSENGER_BUFFER_SIZE in messenger.hh");

    //Copy message into buffer.
    while (dataSize > 0)
    {
      cpSize=msger->processBlock(dataPointer,dataSize,
				 &internalrecvbuf[0],currSize, sock);      
      if ((currSize+cpSize) > MESSENGER_MAX_MSG_SIZE)
	VLOG_WARN(lg, "Message buffer insufficient, check MESSENGER_MAX_MSG_SIZE in messenger.hh");
      else
	VLOG_DBG(lg, "Copy %zu bytes to message",cpSize);

      memcpy(endpointer,dataPointer,cpSize);
      endpointer+=cpSize;
      dataPointer+=cpSize;
      dataSize-=cpSize;
      currSize+=cpSize;

      //End of message
      if ((currSize > 0) &&
	  msger->msg_complete(&internalrecvbuf[0],currSize, sock))
      {
	if (MESSENGER_BYTE_DUMP)
        {
	  fprintf(stderr,"messenger_core message of size %zu\n\t", 
		  currSize);
	  uint8_t* readhead =  internalrecvbuf;
	  for (int i = 0; i < currSize; i++)
	  {
	    fprintf(stderr, "%"PRIx8" ", *readhead);
	    readhead++;
	  }
	  fprintf(stderr,"\n");
	}

	process(new Msg_event((messenger_msg*) internalrecvbuf, sock,
			      currSize));
	endpointer = &internalrecvbuf[0];
	currSize=0;
      }
    }
  }

  void messenger_connection::process(const Msg_event* msg)
  {
    lastActiveTime = time(NULL);
    echoMissed = 0;

    switch (((Msg_event*)msg)->msg->type)
    {
    case MSG_DISCONNECT:
      running = false;
      VLOG_DBG(lg, "Received disconnection request");
    default:
      msger->process(msg);
    }
  }

} // namespace vigil

namespace noxsup
{
  REGISTER_COMPONENT(vigil::container::
		     Simple_component_factory<vigil::messenger_core>, 
		     vigil::messenger_core);
}
