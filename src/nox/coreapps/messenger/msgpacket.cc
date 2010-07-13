#include "msgpacket.hh"

namespace vigil
{
  static Vlog_module lg("msgpacket");

  void msgpacket::configure(const Configuration* config)
  { }

  void msgpacket::init(boost::shared_array<uint8_t>& msg_raw, ssize_t size)
  {
    msg_raw.reset(new uint8_t[size]);
  }

  void msgpacket::init(boost::shared_array<uint8_t>& msg_raw, const char* str, 
		       ssize_t size, bool addbraces)
  {
    if (size == 0)
    {
      size = strlen(str)+1;
      if (addbraces)
	size += 2;
    }
    msg_raw.reset(new uint8_t[size]);
    char* msg = (char*) msg_raw.get();
    if (addbraces)
    {
      msg[0] = '{';
      strcpy(msg+1, str); 
      msg[size-2] = '}';
    }
    else
      strcpy(msg, str); 
    msg[size-1] = '\0';
  }

  void msgpacket::send(boost::shared_array<uint8_t>& msg, Async_stream* sock,
		       ssize_t size)
  {
    Nonowning_buffer buf(msg.get(), size);
    sock->write(buf, 0);
    VLOG_DBG(lg, "Sent message %p of length %zu socket %p",
	     msg.get(), size, sock);
  }

  void msgpacket::send(const std::string& str, Async_stream* sock)
  {
    Nonowning_buffer buf(str.c_str(), str.size());
    sock->write(buf, 0);
    VLOG_DBG(lg, "Sent string of length %zu socket %p",
	     str.size(), sock);
  }

  void msgpacket::getInstance(const container::Context* ctxt,
			      msgpacket*& ofp)
  {
    ofp = dynamic_cast<msgpacket*>
      (ctxt->get_by_interface(container::Interface_description
			      (typeid(msgpacket).name())));
  }
}


REGISTER_COMPONENT(vigil::container::Simple_component_factory
		   <vigil::msgpacket>,
		   vigil::msgpacket);
