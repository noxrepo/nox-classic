/* Copyright 2008 (C) Nicira, Inc.
 *
 * This file is part of NOX.
 *
 * NOX is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * NOX is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with NOX.  If not, see <http://www.gnu.org/licenses/>.
 */
#include "event-dispatcher-component.hh"

#include "datapath-join.hh"
#include "datapath-leave.hh"
#include "error-event.hh"
#include "bootstrap-complete.hh"
#include "flow-removed.hh"
#include "flow-mod-event.hh"
#include "packet-in.hh"
#include "port-status.hh"
#include "shutdown-event.hh"
#include "table-stats-in.hh"
#include "aggregate-stats-in.hh"
#include "desc-stats-in.hh"
#include "flow-stats-in.hh"
#include "ofmp-config-update.hh"
#include "ofmp-config-update-ack.hh"
#include "ofmp-resources-update.hh"
#include "port-stats-in.hh"
#include "switch-mgr-join.hh"
#include "switch-mgr-leave.hh"
#include "barrier-reply.hh"
#include "openflow-msg-in.hh"

#include "nox.hh"
#include "vlog.hh"
#include "xml-util.hh"

#include <iostream>

using namespace std;
using namespace vigil;
using namespace vigil::container;
using namespace xercesc;

static Vlog_module lg("event-dispatcher-c");

EventDispatcherComponent::EventDispatcherComponent(const Context* c,
                                                   const xercesc::DOMNode* 
                                                   platformconf) 
    : Component(c) {

        
    // First construct the 'filter sequences' defined the XML
    // configuration file.
    const DOMNode* nox = xml::get_child_by_tag(platformconf, "nox");
    assert(nox);
    const DOMNode* events = xml::get_child_by_tag(nox, "events");
    assert(events);
    DOMNodeList* l = events->getChildNodes();
    assert(l);
    
    for (XMLSize_t i = 0; i < l->getLength(); ++i) {
        DOMNode* event = l->item(i);
        assert(event);
        if (event->getNodeType() != DOMNode::ELEMENT_NODE) { continue; }

        list<DOMNode*> fl = xml::get_children_by_tag(event, "filter");
        DOMNamedNodeMap* attributes = event->getAttributes();
        assert(attributes);
        string event_name = xml::to_string
            ((static_cast<DOMAttr*>
              (attributes->getNamedItem(XMLString::transcode("name"))))->
             getTextContent()); 

        int order = 0;

        EventFilterChain chain;
        for (list<DOMNode*>::iterator j = fl.begin(); j != fl.end(); ++j) {
            string filter = xml::to_string((*j)->getTextContent()); 
            chain[filter] = order++;
        }

        filter_chains[event_name] = chain;
    }    

    // Register the system events
    register_event<Datapath_join_event>();
    register_event<Datapath_leave_event>();
    register_event<Error_event>();
    register_event<Flow_removed_event>();
    register_event<Flow_mod_event>();
    register_event<Packet_in_event>();
    register_event<Port_status_event>();
    register_event<Shutdown_event>();
    register_event<Bootstrap_complete_event>();
    register_event<Flow_stats_in_event>();
    register_event<Table_stats_in_event>();
    register_event<Ofmp_config_update_event>();
    register_event<Ofmp_config_update_ack_event>();
    register_event<Ofmp_resources_update_event>();
    register_event<Port_stats_in_event>();
    register_event<Aggregate_stats_in_event>();
    register_event<Desc_stats_in_event>();
    register_event<Switch_mgr_join_event>();
    register_event<Switch_mgr_leave_event>();
    register_event<Barrier_reply_event>();
    register_event<Openflow_msg_event>();
}

Component*
EventDispatcherComponent::instantiate(const Context* ctxt, 
                                      const xercesc::DOMNode* platform_conf) {
    return new EventDispatcherComponent(ctxt, platform_conf);
}

void 
EventDispatcherComponent::getInstance(const Context* ctxt, 
                                      EventDispatcherComponent*& edc) {
    edc = dynamic_cast<EventDispatcherComponent*>
        (ctxt->get_by_interface(container::Interface_description
                                (typeid(EventDispatcherComponent).name())));
}

void
EventDispatcherComponent::configure(const container::Configuration*) {
    
}

void
EventDispatcherComponent::install() {

}

void
EventDispatcherComponent::post(Event* event) const {
    // Not needed yet, component class uses still nox::post
    // directly. TBD.
}

bool
EventDispatcherComponent::register_event(const Event_name& name) const {
    if (events.find(name) != events.end()) {
        return false;
    } else {
        events.insert(name);
        return true;
    }
}

bool
EventDispatcherComponent::register_handler(const Component_name& filter,
                                           const Event_name& name,
                                           const Event_handler& h) const {
    if (events.find(name) == events.end()) {
        return false;
    }

    if (filter_chains.find(name) == filter_chains.end()) {
        nox::register_handler(name, h, 0);
    } else {
        EventFilterChain& chain = filter_chains[name];
        if (chain.find(filter) == chain.end()) {
            nox::register_handler(name, h, 0);
        } else {
            nox::register_handler(name, h, chain[filter]);
        }
    }

    return true;
}

/*EventDispatcherComponentFactory::EventDispatcherComponentFactory(const xercesc::DOMNode* conf_)
    : conf(conf_) { }

container::Component* 
EventDispatcherComponentFactory::instance(const container::Context* c, 
                                          const xercesc::DOMNode* xml) const { 
    return new EventDispatcherComponent(c, 
                                        //string(typeid(EventDispatcherComponent).name()), 
                                        //name, 
                                        conf);
}

void
EventDispatcherComponentFactory::destroy(container::Component*) const { 
ctxt->install(from,() */
