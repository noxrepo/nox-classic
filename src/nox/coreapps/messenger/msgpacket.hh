#ifndef msgpacket_HH
#define msgpacket_HH 1

#include "component.hh"
#include "config.h"
#include <xercesc/dom/DOM.hpp>
#include <boost/shared_array.hpp>
#include "messenger_core.hh"

#ifdef LOG4CXX_ENABLED
#include <boost/format.hpp>
#include "log4cxx/logger.h"
#else
#include "vlog.hh"
#endif

namespace vigil
{
  using namespace vigil::container;

  /** \brief Class to pack packets for messenger.
   * 
   * @author ykk
   * @date February 2009
   */
  class msgpacket
    : public container::Component 
  {
  public:
    /** Constructor.
     * @param c context as required by Component
     * @param node Xercesc DOMNode
     */
    msgpacket(const Context* c, const xercesc::DOMNode* node)
        : Component(c) 
    {}

    /** Configure component
     * Register events.
     * @param config configuration
     */
    void configure(const Configuration* config);

    /** Start component.
     */
    void install() 
    {}

    /** Initialize packet with size and type.
     * @param msg_raw message buffer reference
     * @param size size of buffer to allocate
     * @param type type of packet
     */
    void init(boost::shared_array<uint8_t>& msg_raw, ssize_t size, uint8_t type);

    /** Send packet on given socket.
     * @param msg message buffer reference
     * @param sock Async_stream socket
     */
    void send(boost::shared_array<uint8_t>& msg, Async_stream* sock);

    /** Get instance.
     * @param ctxt context
     * @param component reference to packet
     */
    static void getInstance(const container::Context* ctxt, msgpacket*& component);
    
  private:
  };
}
#endif
