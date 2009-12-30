#include "datapathmem.hh"
#include "assert.hh"
#include "datapath-leave.hh"
#include <boost/bind.hpp>

namespace vigil
{
  static Vlog_module lg("datapathmem");

  datapathmem::~datapathmem()
  {
    hash_map<uint64_t,Datapath_join_event>::iterator i = dp_events.begin();
    while (i != dp_events.end())
    {
      dp_events.erase(i);
      i++;
    }
  }

  void datapathmem::configure(const Configuration* c) 
  {
    register_handler<Datapath_join_event>
      (boost::bind(&datapathmem::handle_dp_join, this, _1));
    register_handler<Datapath_leave_event>
      (boost::bind(&datapathmem::handle_dp_leave, this, _1));
  }
  
  void datapathmem::install()
  {
  }

  void datapathmem::getInstance(const Context* c,
				  datapathmem*& component)
  {
    component = dynamic_cast<datapathmem*>
      (c->get_by_interface(container::Interface_description
			      (typeid(datapathmem).name())));
  }

  Disposition datapathmem::handle_dp_join(const Event& e)
  {
    const Datapath_join_event& dje = assert_cast<const Datapath_join_event&>(e);
    
    VLOG_DBG(lg, "Datapath %"PRIx64" joins",dje.datapath_id.as_host());

    hash_map<uint64_t,Datapath_join_event>::iterator i = dp_events.find(dje.datapath_id.as_host());
    if (i == dp_events.end())
      dp_events.insert(make_pair(dje.datapath_id.as_host(),
				 Datapath_join_event(dje)));
    else
      VLOG_WARN(lg, "Duplicate datapath join from %"PRIx64" ignored!",
		dje.datapath_id.as_host());

    return CONTINUE;
  }

  Disposition datapathmem::handle_dp_leave(const Event& e)
  {
    const Datapath_leave_event& dle = assert_cast<const Datapath_leave_event&>(e);

    VLOG_DBG(lg, "Datapath %"PRIx64" leaves",dle.datapath_id.as_host());
    
    hash_map<uint64_t,Datapath_join_event>::iterator i = dp_events.find(dle.datapath_id.as_host());
    if (i != dp_events.end())
      dp_events.erase(i);
    else
      VLOG_WARN(lg, "Datapath leave from unknown switch %"PRIx64" ignored!",
		dle.datapath_id.as_host());
    
    return CONTINUE;
  }

  REGISTER_COMPONENT(Simple_component_factory<datapathmem>,
		     datapathmem);
} // vigil namespace
