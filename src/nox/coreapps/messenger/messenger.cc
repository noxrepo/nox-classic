#include "messenger.hh"
#include "vlog.hh"
#include "assert.hh"
#include <sstream>
#include <boost/foreach.hpp>

namespace vigil
{
  using namespace vigil::container;    

  static Vlog_module lg("messenger");
  static const std::string app_name("messenger");

  messenger::messenger(const Context* c, const xercesc::DOMNode* node): 
    message_processor(c,node)
  { 
    idleInterval = MESSENGER_ECHO_IDLE_THRESHOLD;
    thresholdEchoMissed = MESSENGER_ECHO_THRESHOLD;
    newConnectionMsg = MSG_ON_NEW_CONNECTION;
  };
  
  void messenger::configure(const Configuration* config)
  {
    resolve(msg_core);
    resolve(msger);

    register_handler<Msg_event>
      (boost::bind(&messenger::handle_message, this, _1));

    //Get default port configuration
    if (ENABLE_TCP_MESSENGER)
      tcpport = MESSENGER_PORT;
    else
      tcpport = 0;
    if (ENABLE_SSL_MESSENGER)
      sslport = MESSENGER_SSL_PORT;
    else
      sslport = 0;

    //Get commandline arguments
    BOOST_FOREACH (const std::string& arg_str, config->get_arguments())
    {
      //Get each argument
      std::stringstream args(arg_str); 
      std::string arg;
      int argcount = 0;
      while (getline(args, arg, ',')) 
      {
	//Look into each argument
        std::stringstream argsplit(arg);
        std::string argid, argval, tmparg;
	while (getline(argsplit, tmparg, '=')) 
	{
	  switch (argcount)
	  {
	  case 0:
	    argid=tmparg;
	    break;
	  case 1:
	    argval=tmparg;
	    break;
	  default:
	    VLOG_WARN(lg, "Peculiar argument %s", arg.c_str());
	  }
	  argcount++;
	}
	//Check for known arguments
	if (argid == "tcpport")
	  tcpport = (uint16_t) atoi(argval.c_str());
	else if (argid == "sslport")
	  sslport = (uint16_t) atoi(argval.c_str());
	else
	  VLOG_WARN(lg, "Unknown argument %s = %s", 
		   argid.c_str(), argval.c_str());
      }
    }
  }

  void messenger::install() 
  {
    if (tcpport != 0)
      msg_core->start_tcp(this, tcpport);
    
    if (sslport != 0)
    {
      boost::shared_ptr<Ssl_config> config(new Ssl_config(Ssl_config::ALL_VERSIONS,
							  Ssl_config::NO_SERVER_AUTH,
							  Ssl_config::NO_CLIENT_AUTH,
							  "nox/coreapps/messenger/serverkey.pem",
							  "nox/coreapps/messenger/servercert.pem",
							  "nox/coreapps/messenger/cacert.pem"));
      msg_core->start_ssl(this, sslport, config);
    }
  }
  
  void messenger::process(const Msg_event* msg)
  {
    VLOG_DBG(lg, "Message posted as Msg_event");
    post((Msg_event*) msg);
  }

  void messenger::send_echo(Async_stream* sock)
  {
    VLOG_DBG(lg, "Sending echo on idle socket");
    msger->init(raw_msg, sizeof(messenger_msg), MSG_ECHO);
    msger->send(raw_msg, sock);	
  }

  Disposition messenger::handle_message(const Event& e)
  {
    const Msg_event& me = assert_cast<const Msg_event&>(e);

    if (ntohs(me.msg->length) == 0)
    {
      VLOG_DBG(lg, "New connection message");
      return CONTINUE;
    }

    switch (me.msg->type)
    {
    case MSG_DISCONNECT:
      return STOP;
      break;
    case MSG_ECHO:
      VLOG_DBG(lg, "Got echo request");
      reply_echo(me);
      return STOP;
      break;
    case MSG_ECHO_RESPONSE:
      VLOG_DBG(lg, "Echo reply received");
      return STOP;
      break;
    case MSG_NOX_STR_CMD:
      char mstring[ntohs(me.msg->length)-sizeof(messenger_msg)+1];
      memcpy(mstring, me.msg->body, ntohs(me.msg->length)-sizeof(messenger_msg));
      mstring[ntohs(me.msg->length)-sizeof(messenger_msg)] = '\0';
      VLOG_DBG(lg, "Received string %s", mstring);
      break;
    }

    return CONTINUE;
  }

  void messenger::reply_echo(const Msg_event& echoreq)
  {
    msger->init(raw_msg, sizeof(messenger_msg), MSG_ECHO_RESPONSE);
    msger->send(raw_msg, echoreq.sock->stream);	
  }

  
  void messenger::getInstance(const container::Context* ctxt, 
			      vigil::messenger*& scpa) 
  {
    scpa = dynamic_cast<messenger*>
      (ctxt->get_by_interface(container::Interface_description
			      (typeid(messenger).name())));
  }
}

namespace noxsup
{
  REGISTER_COMPONENT(vigil::container::
		     Simple_component_factory<vigil::messenger>, 
		     vigil::messenger);
}
