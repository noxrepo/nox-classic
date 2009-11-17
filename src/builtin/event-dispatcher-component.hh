#ifndef EVENTC_HH
#define EVENTC_HH 1

#include <list>
#include <string>

#include <xercesc/dom/DOM.hpp>

#include "component.hh"
//#include "container.hh"
#include "event.hh"
#include "hash_map.hh"
#include "hash_set.hh"

namespace vigil {

class ComponentConfiguration;

/**
 * Event dispatcher component is responsible for event management.
 *
 * TODO: merge in the lib/event-dispatcher.cc and rename the
 * class/file. Do the same for lib/timer-dispatcher.cc.
 */
class EventDispatcherComponent
    : public container::Component {
public:
    /* Construct a new component instance. For nox::main() */
    static container::Component* instantiate(const container::Context*,
                                             const xercesc::DOMNode*);
    
    static void getInstance(const container::Context*, 
                            EventDispatcherComponent*&);
    
    void configure(const container::Configuration*);
    void install();

    /* Post an event */
    void post(Event*) const;

    /* Register an event */
    template <typename T>
    inline 
    void register_event() const {
        register_event(T::static_get_name());
    }

    /* Register an event */
    bool register_event(const Event_name&) const;
       
    /* Register an event handler */
    bool register_handler(const container::Component_name&,
                          const Event_name&,
                          const Event_handler&) const;
    
private:
    EventDispatcherComponent(const container::Context*,const xercesc::DOMNode*);

    /* Configured event filter chains */
    typedef std::string EventName;
    typedef hash_map<container::Component_name, int> EventFilterChain;
    mutable hash_map<EventName, EventFilterChain> filter_chains;

    /* Registered events */
    mutable hash_set<EventName> events;
};

    /*class EventDispatcherComponentFactory
    : public container::Component_factory {
public:
    EventDispatcherComponentFactory(const xercesc::DOMNode*);

    container::Component* instance(const container::Context*, 
                                   const xercesc::DOMNode*) const;

    void destroy(container::Component*) const; 

private:
    const xercesc::DOMNode *conf;
    };*/

}

#endif
