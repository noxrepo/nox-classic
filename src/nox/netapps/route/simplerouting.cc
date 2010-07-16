#include "simplerouting.hh"
#include "assert.hh"
#include "netinet++/ethernet.hh"
#include <boost/bind.hpp>

namespace vigil
{
  static Vlog_module lg("simplerouting");
  
  void simplerouting::configure(const Configuration* c) 
  {
    resolve(ht);
    resolve(ri);

    register_handler<Packet_in_event>
      (boost::bind(&simplerouting::handle_pkt_in, this, _1));
  }
  
  Disposition simplerouting::handle_pkt_in(const Event& e)
  {
    const Packet_in_event& pie = assert_cast<const Packet_in_event&>(e);

    //Skip LLDP
    if (pie.flow.dl_type == ethernet::LLDP)
      return CONTINUE;

    const hosttracker::location sloc = ht->get_latest_location(pie.flow.dl_src);
    const hosttracker::location dloc = ht->get_latest_location(pie.flow.dl_dst);
    bool routed = false;

    //Route or at least try
    if (!sloc.dpid.empty() && !dloc.dpid.empty())
    {      
      network::route rte(sloc.dpid, sloc.port);
      network::termination endpt(dloc.dpid, dloc.port);
      if (ri->get_shortest_path(endpt, rte))
      {
      	ri->install_route(pie.flow, rte, pie.buffer_id);
	routed = true;
      }
    }

    //Failed to route, flood
    if (!routed)
    {
      //Flood
      VLOG_DBG(lg, "Sending packet of %s via control",
	       pie.flow.to_string().c_str());
      if (pie.buffer_id == ((uint32_t) -1))
	send_openflow_packet(pie.datapath_id, *(pie.buf),
			     OFPP_FLOOD, pie.in_port, false);
      else
	send_openflow_packet(pie.datapath_id, pie.buffer_id,
			     OFPP_FLOOD, pie.in_port, false);	
    }

    return CONTINUE;
  }

  void simplerouting::install()
  {
  }

  void simplerouting::getInstance(const Context* c,
				  simplerouting*& component)
  {
    component = dynamic_cast<simplerouting*>
      (c->get_by_interface(container::Interface_description
			      (typeid(simplerouting).name())));
  }

  REGISTER_COMPONENT(Simple_component_factory<simplerouting>,
		     simplerouting);
} // vigil namespace
