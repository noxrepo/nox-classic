#include "lavi_hosts.hh"
#include "assert.hh"

namespace vigil
{
  static Vlog_module lg("lavi_hosts");
  
  void lavi_hosts::configure(const Configuration* c) 
  {
    nodetype = "host";

    resolve(ht);
    resolve(mp);
  }
  
  void lavi_hosts::install()
  {
  }

  void lavi_hosts::send_list(const Msg_stream& stream)
  {
    send_hostlist(stream, ht->get_hosts());
  }

  void lavi_hosts::send_hostlist(const Msg_stream& stream, 
				 const list<ethernetaddr> host_list,
				 bool add)
  {
    VLOG_DBG(lg, "Sending host list of %zu to %p", host_list.size(), &stream);

    json_object jm(json_object::JSONT_DICT);
    json_dict* jd = new json_dict();
    jm.object = jd;
    json_object* jo;
    json_object* jv;
    char buf[20];

    //Add type
    jo = new json_object(json_object::JSONT_STRING);
    jo->object = new string("lavi");
    jd->insert(make_pair("type", jo));

    //Add command
    jo = new json_object(json_object::JSONT_STRING);
    if (add)
      jo->object = new string("add");
    else
      jo->object = new string("delete");      
    jd->insert(make_pair("command", jo));

    //Add node_type
    jo = new json_object(json_object::JSONT_STRING);
    jo->object = new string(nodetype);
    jd->insert(make_pair("node_type", jo));

    //Add string of host mac
    jo = new json_object(json_object::JSONT_ARRAY);
    json_array* ja = new json_array();
    for (list<ethernetaddr>::const_iterator i = host_list.begin();
	 i != host_list.end(); i++)
    {
      jv = new json_object(json_object::JSONT_STRING);
      sprintf(buf,"%"PRIx64"", i->hb_long());
      jv->object = new string(buf);
      ja->push_back(jv);
    }
    jo->object = ja;
    VLOG_DBG(lg, "Size %zu: %s",  ja->size(), jo->get_string().c_str());
    jd->insert(make_pair("node_id", jo));

    //Send
    VLOG_DBG(lg, "Sending reply: %s", jm.get_string().c_str());
    mp->send(jm.get_string(),stream.stream);
  }

  void lavi_hosts::getInstance(const Context* c,
				  lavi_hosts*& component)
  {
    component = dynamic_cast<lavi_hosts*>
      (c->get_by_interface(container::Interface_description
			      (typeid(lavi_hosts).name())));
  }

  REGISTER_COMPONENT(Simple_component_factory<lavi_hosts>,
		     lavi_hosts);
} // vigil namespace
