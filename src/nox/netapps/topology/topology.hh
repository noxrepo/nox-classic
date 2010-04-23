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
#ifndef TOPOLOGY_HH
#define TOPOLOGY_HH 1

#include <list>

#include "component.hh"
#include "hash_map.hh"
#include "discovery/link-event.hh"
#include "netinet++/datapathid.hh"
#include "port.hh"

namespace vigil {
namespace applications {

/** \ingroup noxcomponents
 *
 * The current network topology  
 *
 */



class Topology
    : public container::Component {

public:
    struct LinkPorts {
        uint16_t src;
        uint16_t dst;
    };

    typedef std::vector<Port> PortVector;
    typedef hash_map<uint16_t, std::pair<uint16_t, uint32_t> > PortMap;
    typedef std::list<LinkPorts> LinkSet;
    typedef hash_map<datapathid, LinkSet> DatapathLinkMap;

    struct DpInfo {
        PortVector ports;
        PortMap internal;
        DatapathLinkMap outlinks;
        bool active;
    };

    Topology(const container::Context*, const json_object*);

    static void getInstance(const container::Context*, Topology*&);

    void configure(const container::Configuration*);
    void install();

    const DpInfo& get_dpinfo(const datapathid& dp) const;
    const DatapathLinkMap& get_outlinks(const datapathid& dpsrc) const;
    const LinkSet& get_outlinks(const datapathid& dpsrc, const datapathid& dpdst) const;

    bool is_internal(const datapathid& dp, uint16_t port) const;

private:
    typedef hash_map<datapathid, DpInfo> NetworkLinkMap;

    NetworkLinkMap topology;
    DpInfo empty_dp;
    LinkSet empty_link_set;

    //Topology() { }

    Disposition handle_datapath_join(const Event&);
    Disposition handle_datapath_leave(const Event&);
    Disposition handle_port_status(const Event&);
    Disposition handle_link_event(const Event&);

    void add_port(const datapathid&, const Port&, bool);
    void delete_port(const datapathid&, const Port&);

    void add_link(const Link_event&);
    void remove_link(const Link_event&);

    void add_internal(const datapathid&, uint16_t);
    void remove_internal(const datapathid&, uint16_t);
};

} // namespace applications
} // namespace vigil

#endif
