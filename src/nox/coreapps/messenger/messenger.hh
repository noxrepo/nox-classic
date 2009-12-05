#ifndef MESSENGER_HH__
#define MESSENGER_HH__

/** Server port number for \ref vigil::messenger.
 */
#define MESSENGER_PORT 2603
/** Server port number for SSL connection in \ref vigil::messenger.
 */
#define MESSENGER_SSL_PORT 1304
/** Enable TCP connection.
 */
#define ENABLE_TCP_MESSENGER true
/** Enable SSL connection.
 */
#define ENABLE_SSL_MESSENGER true
/** Send message when new connections.
 */
#define MSG_ON_NEW_CONNECTION false
/** Idle interval to trigger echo request (in s).
 */
#define MESSENGER_ECHO_IDLE_THRESHOLD 0
/** Echo request non reply threshold to drop connection.
 */
#define MESSENGER_ECHO_THRESHOLD 3

#include "messenger_core.hh"
#include "msgpacket.hh"

namespace vigil
{
  using namespace vigil::container; 
  
  /** \ingroup noxcomponents
   * \brief Class through which to interact with NOX.
   *
   * In NOX, packets can be packed using msgpacket.  Note that each 
   * component that sends messages via messenger should have an array
   * for storing the messages.
   *
   * TCP and SSL port can be changed at commandline using
   * tcpport and sslport arguments for golems respectively. 
   * port 0 is interpreted as disabling the server socket.  
   * E.g.,
   * ./nox_core -i ptcp:6633 messenger=tcport=11222,sslport=0
   * will run TCP server on port 11222 and SSL server will be disabled.
   *
   * Received messages are sent to other components via the Msg_event.
   * This allows extension of the messaging system, with no changes of
   * messenger.
   *
   * Copyright (C) Stanford University, 2009.
   * @author ykk
   * @date May 2009
   * @see messenger_core
   */
  class messenger : public message_processor
  {
  public:
    /** Constructor.
     * Start server socket.
     * @param c context as required by Component
     * @param node Xercesc DOMNode
     */
    messenger(const Context* c, const xercesc::DOMNode* node);

    /** Destructor.
     * Close server socket.
     */
    virtual ~messenger() 
    { };
    
    /** Configure component
     * Register events..
     * @param config configuration
     */
    void configure(const Configuration* config);

    /** Start component.
     * Create messenger_server and starts server thread.
     */
    void install();

    /** Get instance of messenger (for python)
     * @param ctxt context
     * @param scpa reference to return instance with
     */
    static void getInstance(const container::Context* ctxt, 
			    vigil::messenger*& scpa);

    /** Function to do processing for messages received.
     * @param msg message event for message received
     */
    void process(const Msg_event* msg);

    /** Send echo request.
     * @param sock socket to send echo request over
     */
    void send_echo(Async_stream* sock);

    /** Process string type, i.e., print in debug logs.
     * @param e event to be handled
     * @return CONTINUE always
     */
    Disposition handle_message(const Event& e);

    /** Reply to echo request.
     * @param echoreq echo request
     */
    void reply_echo(const Msg_event& echoreq);

  private:
    /** Reference to messenger_core.
     */
    messenger_core* msg_core;
    /** Memory allocated for \ref vigil::bookman messages.
     */
    boost::shared_array<uint8_t> raw_msg;
    /** Reference to msgpacket
     */
    msgpacket* msger;
    /** TCP port number.
     */
    uint16_t tcpport;
    /** SSL port number.
     */
    uint16_t sslport;
  };
}

#endif
