#include "flowroute_record.hh"

namespace vigil
{
  static Vlog_module lg("flowroute_record");

  void flowroute_record::configure(const Configuration* c) 
  {
  }
  
  void flowroute_record::install()
  {
  }

  void flowroute_record::set(const Flow& flow, const network::route& rte,
			     bool throwEvent)
  {
    if (throwEvent)
    {
      if (unset(flow, false))
	post(new Flow_route_event(flow, rte,
				  Flow_route_event::MODIFY));
      else
	post(new Flow_route_event(flow, rte,
				  Flow_route_event::ADD));
    }
    routeMap.insert(make_pair(*(new Flow(flow)), 
			      *(new network::route(rte))));
  }

  bool flowroute_record::unset(const Flow& flow, bool throwEvent)
  {
    hash_map<Flow, network::route>::iterator i = routeMap.find(flow);
    //Existing flow
    if (i != routeMap.end())
    {
      if (throwEvent)
	post(new Flow_route_event(i->first, i->second,
				  Flow_route_event::REMOVE));

      delete &(i->first);
      delete &(i->second);
      routeMap.erase(i);
      
      return true;
    }
    
    return false;
  }

  void flowroute_record::getInstance(const Context* c,
				  flowroute_record*& component)
  {
    component = dynamic_cast<flowroute_record*>
      (c->get_by_interface(container::Interface_description
			      (typeid(flowroute_record).name())));
  }

  REGISTER_COMPONENT(Simple_component_factory<flowroute_record>,
		     flowroute_record);
} // vigil namespace
