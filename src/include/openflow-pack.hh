#ifndef OPENFLOW_PACK_H
#define OPENFLOW_PACK_H

#include "openflow/openflow.h"
#include "buffer.hh"
#include "xtoxll.h"
#include <boost/shared_array.hpp>

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
     * @return xid
     */
    static uint32_t header(boost::shared_array<uint8_t>& of_raw, 
			   uint8_t type, uint16_t length);

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
