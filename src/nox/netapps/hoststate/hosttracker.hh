/* Copyright 20010 (C) Stanford University.
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
#ifndef hosttracker_HH
#define hosttracker_HH

#include "component.hh"
#include "config.h"
#include "netinet++/ethernetaddr.hh"
#include "netinet++/datapathid.hh"
#include "hash_map.hh"
#include <xercesc/dom/DOM.hpp>

#ifdef LOG4CXX_ENABLED
#include <boost/format.hpp>
#include "log4cxx/logger.h"
#else
#include "vlog.hh"
#endif

/** Default number of host locations to store per host
 */
#define DEFAULT_HOST_N_BINDINGS 1
/** Default host timeout (5 min)
 */
#define DEFAULT_HOST_TIMEOUT 300

namespace vigil
{
  using namespace std;
  using namespace vigil::container;

  /** \Brief hosttracker: Track locations of host (ethernet)
   * \ingroup noxcomponents
   * 
   * Track last n known locations of host attachment.
   *
   * @author ykk
   * @date February 2010
   */
  class hosttracker
    : public Component 
  {
  public:
    /** Struct to hold host location.
     */
    struct location
    {
      /** Constructor
       * @param dpid switch datapath id
       * @param port port of switch host is connected to
       * @param tv time of connection/detection
       */
      location(datapathid dpid, uint16_t port, time_t tv);

      /** Empty Constructor
       */
      location():
	dpid(datapathid()), port(0)
      {};

      /** Set value of location
       * @param loc location to copy value from
       */
      void set(const location& loc);

      /** Switch host is located on
       */
      datapathid dpid;
      /** Port host is attached to.
       */
      uint16_t port;
      /** Last known active time
       */
      time_t lastTime;
    };

    /** Host timeout (in s)
     */
    uint16_t hostTimeout;
    /** Default number of bindings to store
     */
    uint8_t defaultnBindings;
    /** Number of binding to store
     */
    hash_map<ethernetaddr,uint8_t> nBindings;

    /** \brief Constructor of hosttracker.
     *
     * @param c context
     * @param node XML configuration (Xercesc DOMNode)
     */
    hosttracker(const Context* c, const xercesc::DOMNode* node)
      : Component(c)
    {}
    
    /** \brief Check host timeout 
     */
    void check_timeout();

    /** \brief Find oldest host.
     * @return ethernet address of host with earliest timeout
     */
    const ethernetaddr oldest_host();

    /** \brief Get number of binding host can have.
     * @param host host as identified by ethernet address
     * @return number of bindings host can have
     */
    uint8_t getBindingNumber(ethernetaddr host);

    /** \brief Retrieve location of host
     * @param host host as identified by ethernet address
     * @return list of location(s)
     */
    const list<location> getLocations(ethernetaddr host);

    /** \brief Set location.
     * @param host host as identified by ethernet address
     * @param loc location host is detected
     */
    void add_location(ethernetaddr host, location loc);

    /** \brief Set location.
     * @param host host as identified by ethernet address
     * @param dpid switch datapath id
     * @param port port of switch host is connected to
     * @param tv time of connection/detection (default to 0 == now)
     */
    void add_location(ethernetaddr host, datapathid dpid, uint16_t port,
		      time_t tv=0);

    /** \brief Get locations
     * @param host ethernet address of host
     * @return locations
     */
    const list<location> get_locations(ethernetaddr host);

    /** \brief Get latest location
     * @param host ethernet address of host
     * @return location (with empty datapath id if no binding found)
     */
    const location get_latest_location(ethernetaddr host);

    /** \brief Configure hosttracker.
     * 
     * Parse the configuration, register event handlers, and
     * resolve any dependencies.
     *
     * @param c configuration
     */
    void configure(const Configuration* c);

    /** \brief Start hosttracker.
     * 
     * Start the component. For example, if any threads require
     * starting, do it now.
     */
    void install();

    /** \brief Get instance of hosttracker.
     * @param c context
     * @param component reference to component
     */
    static void getInstance(const container::Context* c, 
			    hosttracker*& component);

  private:
    /** Ethernet address to location mapping.
     */
    hash_map<ethernetaddr,list<location> > hostlocation;

    /** Get oldest location.
     * @param loclist location list
     * @return pointer to oldest item
     */
    list<location>::iterator get_oldest(list<location>& loclist);

    /** Get newest location.
     * @param loclist location list
     * @return pointer to newest item
     */
    list<location>::iterator get_newest(list<location>& loclist);
  };
}

#endif
