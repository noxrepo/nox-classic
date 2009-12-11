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
#ifndef FLOW_HH
#define FLOW_HH 1

#define IP_ADDR_LEN 4

#include <cstring>
#include <iosfwd>
#include "netinet++/ethernetaddr.hh"
#include "openflow/openflow.h"

namespace vigil {

class Buffer;

struct Flow {
    uint16_t in_port;       /* Input switch port. */
    uint16_t dl_vlan;       /* Input VLAN. */
    uint8_t dl_vlan_pcp;    /* Input VLAN priority. */
    ethernetaddr dl_src;    /* Ethernet source address. */
    ethernetaddr dl_dst;    /* Ethernet destination address. */
    uint16_t dl_type;       /* Ethernet frame type. */
    uint32_t nw_src;        /* IP source address. */
    uint32_t nw_dst;        /* IP destination address. */
    uint8_t nw_proto;       /* IP protocol. */
    uint8_t nw_tos;         /* IP ToS (actually DSCP field, 6 bits). */
    uint16_t tp_src;        /* TCP/UDP source port. */
    uint16_t tp_dst;        /* TCP/UDP destination port. */

    Flow() {} // for Python bindings
    Flow(uint16_t in_port_, const Buffer&);
    Flow(const ofp_match& match);
    Flow(const ofp_match* match);
    Flow(uint16_t in_port_, uint16_t dl_vlan_, uint8_t dl_vlan_pcp_,
            ethernetaddr dl_src_, ethernetaddr dl_dst_, uint16_t dl_type_, 
            uint32_t nw_src_, uint32_t nw_dst_, uint8_t nw_proto_,
            uint16_t tp_src_, uint16_t tp_dst_, uint8_t nw_tos_=0) :
        in_port(in_port_), dl_vlan(dl_vlan_), dl_vlan_pcp(dl_vlan_pcp_), 
        dl_src(dl_src_), dl_dst(dl_dst_), dl_type(dl_type_),
        nw_src(nw_src_), nw_dst(nw_dst_), 
	nw_proto(nw_proto_), nw_tos(nw_tos_),
        tp_src(tp_src_), tp_dst(tp_dst_) { }
    static bool matches(const Flow&, const Flow&);
    const std::string to_string() const;

    uint64_t hash_code() const;
};
bool operator==(const Flow& lhs, const Flow& rhs);
bool operator!=(const Flow& lhs, const Flow& rhs);
std::ostream& operator<<(std::ostream&, const Flow&);

} // namespace vigil

#endif /* flow.hh */
