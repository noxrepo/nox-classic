#ifndef OPENFLOW_PACK_H
#define OPENFLOW_PACK_H

#include "openflow/openflow.h"
#include "openflow-default.hh"
#include "buffer.hh"
#include "flow.hh"
#include "xtoxll.h"
#include "netinet++/datapathid.hh"
#include "netinet++/ethernetaddr.hh"
#include <boost/shared_array.hpp>
#include <stdlib.h>
#include <list>

/** \brief Minimum transaction id.
 *
 * All xid smaller than this value are reserved 
 * and will not be used by ofpack.
 */
#define OPENFLOW_PACK_MIN_XID 256

/** \brief Mode of generating transaction id.
 * 
 * Defaults to increment if not defined.
 */
#define OPENFLOW_PACK_XID_METHOD_INCREMENT 0
#define OPENFLOW_PACK_XID_METHOD_RANDOM 1
#define OPENFLOW_PACK_XID_METHOD OPENFLOW_PACK_XID_METHOD_INCREMENT

namespace vigil
{
  /** \brief Structure to hold OpenFlow action.
   *
   * Copyright (C) Stanford University, 2009.
   * @author ykk
   * @date February 2009
   */
  struct ofp_action
  {
    /** Header of action
     */
    ofp_action_header* header;
    
      /** Pointer to memory for OpenFlow messages.
       */
    boost::shared_array<uint8_t> action_raw;
    
    /** Initialize action.
     */
    ofp_action()
    {}

    /** Set enqueue action, i.e., ofp_action_enqueue.
     * @param port port number of send to
     * @param queueid queue id
     */
    void set_action_enqueue(uint16_t port, uint32_t queueid);
    
    /** Set output action, i.e., ofp_action_output.
     * @param port port number of send to
     * @param max_len maximum length to send to controller
     */
    void set_action_output(uint16_t port, uint16_t max_len);

    /** Set source/destination mac address.
     * @param type OFPAT_SET_DL_SRC or OFPAT_SET_DL_DST
     * @param mac mac address to set to
     */ 
    void set_action_dl_addr(uint16_t type, ethernetaddr mac);

    /** Set source/destination IP address.
     * @param type OFPAT_SET_NW_SRC or OFPAT_SET_NW_DST
     * @param ip ip address to set to
     */ 
    void set_action_nw_addr(uint16_t type, uint32_t ip);
  };
  
  /** \brief List of actions for switches.   
   *
   * Copyright (C) Stanford University, 2009.
   * @author ykk
   * @date February 2009
   */
  struct ofp_action_list
  {
    /** List of actions.
     */
    std::list<ofp_action> action_list;

    /** Give total length of action list, i.e.,
     * memory needed.
     * @return memory length needed for list
     */
    uint16_t mem_size();

    /** Destructor.
     * Clear list of actions.
     */
    ~ofp_action_list()
    {
      action_list.clear();
    }
  };

  class ofpack;
  class ofupack;

  /** \brief Class with static functions to pack OpenFlow messages.
   * \ingroup noxapi
   *
   * Functions handle htonxx.
   *
   * @author ykk
   * @data December 2009
   * @see ofupack
   */
  class ofpack
  {
  public:
    /** \brief Return xid.
     * 
     * @return transaction id for OpenFlow messages
     */
    static uint32_t get_xid();

    /** \brief Pack header
     *
     * @param ofph pointer to OpenFlow header
     * @param type type of message
     * @param length length of message
     * @param version OpenFlow version number
     * @param xid transaction id
     */
    static void header(ofp_header* ofph, uint8_t type,
		       uint16_t length, uint8_t version, uint32_t xid);
    
    /** \brief Pack header
     *
     * Also initialize Boost shared array to appropriate length. 
     *
     * @param of_raw memory to pack message into
     * @param type type of message
     * @param length length of message
     * @param version OpenFlow version number
     * @param xid transaction id
     */
    static void header(boost::shared_array<uint8_t>& of_raw, uint8_t type,
		       uint16_t length, uint8_t version, uint32_t xid);

    /** \brief Pack header
     *
     * Also initialize Boost shared array to appropriate length. 
     *
     * @param of_raw memory to pack message into
     * @param type type of message
     * @param length length of message
     * @param version OpenFlow version number
     * @return xid
     */
    static uint32_t header(boost::shared_array<uint8_t>& of_raw, 
			   uint8_t type, uint16_t length,
			   uint8_t version=OFP_VERSION);

    /** \brief Pack flow mod
     * @param of_raw memory to pack message into
     * @param list list of actions
     */
    static void flow_mod(boost::shared_array<uint8_t>& of_raw, 
			 ofp_action_list list);

    /**\brief Set exact match from flow for flow mod
     * @param of_raw buffer/memory for message
     * @param flow reference to flow to match to
     * @param buffer_id buffer id of flow
     * @param in_port input port
     * @param cookie opaque id
     * @param out_port out port
     * @param command command in flow_mod
     * @param idle_timeout idle timeout
     * @param hard_timeout hard timeout
     * @param priority priority of entry
     * @param wildcards wildcards flags
     */
    static void flow_mod_exact(boost::shared_array<uint8_t>& of_raw, 
			       const Flow& flow, uint32_t buffer_id, 
			       uint16_t in_port, uint16_t command,
			       uint64_t cookie=0,
			       uint16_t out_port=OFPP_NONE,
			       uint16_t idle_timeout=DEFAULT_FLOW_TIMEOUT, 
			       uint16_t hard_timeout=0, 
			       uint16_t priority=OFP_DEFAULT_PRIORITY,
			       uint32_t wildcards=0);

    /** \brief Set actions for flow mod
     * @param of_raw buffer/memory for message
     * @param list list of actions
     */
    static void flow_mod_actions(boost::shared_array<uint8_t>& of_raw, 
				 ofp_action_list list);

    /** \brief Set stats request.
     * @param type type of stats request
     * @param flags flags
     */
    static void stat_req(boost::shared_array<uint8_t>& of_raw,
			 uint16_t type, uint16_t flags=0);

    /** \brief Pack port stats request.
     * @param port port to request stats for
     * @param flags flags
     */
    static void port_stat_req(boost::shared_array<uint8_t>& of_raw,
			      uint16_t port=OFPP_NONE, uint16_t flags=0);

    /** \brief Get OpenFlow header pointer.
     *
     * @return pointer to OpenFlow header
     */
    static inline ofp_header* get_ofph(boost::shared_array<uint8_t>& of_raw)
    {
      return (ofp_header*) of_raw.get();
    }

    /** \brief Change xid.
     *
     * @param ofph pointer to OpenFlow header
     * @param xid_ transaction id
     */
    static inline void xid(ofp_header* ofph, uint32_t xid_)
    {
      ofph->xid = htonl(xid_);
    }

    /** \brief Change xid
     *
     * @param of_raw memory to pack message into
     * @param xid_ transaction id
     */
    static inline void xid(boost::shared_array<uint8_t>& of_raw, 
			   uint32_t xid_)
    {
      xid(get_ofph(of_raw), xid_);
    }

    /** \brief Change to new xid.
     * 
     * @param ofph pointer to OpenFlow header
     */
    static inline uint32_t xid(ofp_header* ofph)
    {
      return ntohl(ofph->xid = htonl(get_xid()));
    }

    /** \brief Change to new xid.
     * 
     * @param of_raw memory to pack message into
     */
    static inline uint32_t xid(boost::shared_array<uint8_t>& of_raw)
    {
      return xid(get_ofph(of_raw));
    }


  private:
    /** \brief Next transaction id if increment one are used
     *
     * @see ofpack
     */
    static uint32_t nextxid;
    /** \brief Generate random 32-bit number.
     *
     * @return random unsigned 32-bit number.
     */
    static uint32_t rand_uint32();
  };

  /** \brief Class with static functions to unpack OpenFlow messages.
   * \ingroup noxapi
   *
   * Functions handle ntohxx.
   * All returned values are in host order.
   *
   * @author ykk
   * @data December 2009
   * @see ofpack
   */
  class ofupack
  {
  public:
    /** \brief Return transaction id
     *
     * @param buf buffer message is stored in
     * @return xid
     */
    static inline uint32_t xid(const Buffer& buf)
    {
      return xid((ofp_header*) buf.data());
    }
    
    /** \brief Return transaction id
     *
     * @param ofph pointer of OpenFlow header (in network order)
     * @return xid
     */
    static inline uint32_t xid(ofp_header* ofph)
    {
      return ntohl(ofph->xid);
    }

    /** \brief Return OpenFlow header
     *
     * @param buf buffer message is stored in
     * @return OpenFlow header
     */
    static inline ofp_header header(const Buffer& buf)
    {
      return header((ofp_header*) buf.data());
    }

    /** \brief Return OpenFlow header
     *
     * @param ofph pointer of OpenFlow header (in network order)
     * @return OpenFlow header
     */
    static ofp_header header(ofp_header* ofph);

  private:
  };
			     
} // namespace vigil

#endif
