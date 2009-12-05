#include "msgpacket.hh"

namespace vigil
{
  static Vlog_module lg("msgpacket");

  void msgpacket::configure(const Configuration* config)
  { }

  void msgpacket::init(boost::shared_array<uint8_t>& msg_raw, ssize_t size, uint8_t type)
  {
    msg_raw.reset(new uint8_t[size]);
    messenger_msg* mmsg = (messenger_msg*) msg_raw.get();
    mmsg->length = htons(size);
    mmsg->type = type;
  }

  void msgpacket::send(boost::shared_array<uint8_t>& msg, Async_stream* sock)
  {
    messenger_msg* mmsg = (messenger_msg*) msg.get();
    Nonowning_buffer buf(mmsg, ntohs(mmsg->length));
    sock->write(buf, 0);
    VLOG_DBG(lg, "Sent message %p of length %"PRIx16" with type %"PRIx8" over socket %p",
	     msg.get(), ntohs(mmsg->length), mmsg->type, sock);
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
