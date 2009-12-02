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
#include "flow.hh"

#include <string>
#include <ostream>
#include <stdexcept>

#include "netinet++/ethernet.hh"
#include "netinet++/ip.hh"

#include <netinet/in.h>

#include "vlog.hh"
#include "buffer.hh"
#include "openflow/openflow.h"
#include "packets.h"
#include "vlog.hh"
#include "openssl/md5.h"

namespace vigil {

static Vlog_module log("flow");

static const ip_header *
pull_ip(Buffer& b)
{
    if (const ip_header *ip = b.try_at<ip_header>(0)) {
        int ip_len = IP_IHL(ip->ip_ihl_ver) * 4;
        if (ip_len >= sizeof *ip) {
            return reinterpret_cast<const ip_header*>(b.try_pull(ip_len));
        }
    }
    return 0;
}

static const tcp_header *
pull_tcp(Buffer& b)
{
    if (const tcp_header *tcp = b.try_at<tcp_header>(0)) {
        int tcp_len = TCP_OFFSET(tcp->tcp_ctl) * 4;
        if (tcp_len >= sizeof *tcp) {
            return reinterpret_cast<const tcp_header*>(b.try_pull(tcp_len));
        }
    }
    return 0;
}

static const udp_header *
pull_udp(Buffer& b)
{
    return b.try_pull<udp_header>();
}

static const icmp_header *
pull_icmp(Buffer& b)
{
    return b.try_pull<icmp_header>();
}

static const eth_header *
pull_eth(Buffer& b)
{
    return b.try_pull<eth_header>();
}

static const vlan_header *
pull_vlan(Buffer& b)
{
    return b.try_pull<vlan_header>();
}

Flow::Flow(uint16_t in_port_, const Buffer& buffer)
    : in_port(in_port_),
      dl_vlan(), dl_vlan_pcp(0), dl_src(), dl_dst(), dl_type(0),
      nw_src(0), nw_dst(0), nw_proto(0),
      tp_src(0), tp_dst(0)
{
    dl_vlan = htons(OFP_VLAN_NONE);

    Nonowning_buffer b(buffer);
    const eth_header* eth = pull_eth(b);
    if (eth) {
        if (ntohs(eth->eth_type) >= ethernet::ETH2_CUTOFF) {
            /* This is an Ethernet II frame */
            dl_type = eth->eth_type;
        } else {
            /* This is an 802.2 frame */
            const llc_snap_header *h = b.try_at<llc_snap_header>(0);
            if (h == NULL) {
                goto end;
            }
            if (h->llc.llc_dsap == LLC_DSAP_SNAP
                && h->llc.llc_ssap == LLC_SSAP_SNAP
                && h->llc.llc_cntl == LLC_CNTL_SNAP
                && !memcmp(h->snap.snap_org, SNAP_ORG_ETHERNET,
                           sizeof h->snap.snap_org)) {
                dl_type = h->snap.snap_type;
                b.pull(sizeof *h);
            } else {
                dl_type = htons(OFP_DL_TYPE_NOT_ETH_TYPE);
                b.pull(sizeof(llc_header));
            }
        }

        /* Check for a VLAN tag */
        if (dl_type == htons(ETH_TYPE_VLAN)) {
            const vlan_header *vh = pull_vlan(b);
            if (vh) {
                dl_type = vh->vlan_next_type;
                dl_vlan = vh->vlan_tci & htons(VLAN_VID);
            }
        }
        memcpy(dl_src.octet, eth->eth_src, ETH_ADDR_LEN);
        memcpy(dl_dst.octet, eth->eth_dst, ETH_ADDR_LEN);

        if (dl_type == htons(ETH_TYPE_IP)) {
            const ip_header *ip = pull_ip(b);
            if (ip) {
                nw_src = ip->ip_src;
                nw_dst = ip->ip_dst;
                nw_proto = ip->ip_proto;
                if (!ip_::is_fragment(ip->ip_frag_off)) {
                    if (nw_proto == ip_::proto::TCP) {
                        const tcp_header *tcp = pull_tcp(b);
                        if (tcp) {
                            tp_src = tcp->tcp_src;
                            tp_dst = tcp->tcp_dst;
                        } else {
                            /* Avoid tricking other code into thinking that
                             * this packet has an L4 header. */
                            nw_proto = 0;
                        }
                    } else if (nw_proto == ip_::proto::UDP) {
                        const udp_header *udp = pull_udp(b);
                        if (udp) {
                            tp_src = udp->udp_src;
                            tp_dst = udp->udp_dst;
                        } else {
                            /* Avoid tricking other code into thinking that
                             * this packet has an L4 header. */
                            nw_proto = 0;
                        }
                    } else if (nw_proto == ip_::proto::ICMP) {
                        const icmp_header *icmp = pull_icmp(b);
                        if (icmp) {
                            icmp_type = htons(icmp->icmp_type);
                            icmp_code = htons(icmp->icmp_code);
                        } else {
                            /* Avoid tricking other code into thinking that
                             * this packet has an L4 header. */
                            nw_proto = 0;
                        }
                    }
                }
            }
        }
    }

end:
    if (buffer.size() < (ETH_HEADER_LEN)) {
        log.err("Packet length %zu less than minimum Ethernet packet %d: %s",
                 buffer.size(), ETH_HEADER_LEN,
                 to_string().c_str());
    }
}

const std::string
Flow::to_string() const
{
    char buffer[128];
    snprintf(buffer, sizeof buffer,
	     "port%04x:vlan%04x:pcp:%d mac"EA_FMT"->"EA_FMT" "
	     "proto%04x ip%u.%u.%u.%u->%u.%u.%u.%u port%d->%d",
	     ntohs(in_port), ntohs(dl_vlan), dl_vlan_pcp,
		 EA_ARGS(&dl_src), EA_ARGS(&dl_dst),
	     ntohs(dl_type),
	     ((unsigned char *)&nw_src)[0],
	     ((unsigned char *)&nw_src)[1],
	     ((unsigned char *)&nw_src)[2],
	     ((unsigned char *)&nw_src)[3],
	     ((unsigned char *)&nw_dst)[0],
	     ((unsigned char *)&nw_dst)[1],
	     ((unsigned char *)&nw_dst)[2],
	     ((unsigned char *)&nw_dst)[3],
	     ntohs(tp_src), ntohs(tp_dst));
    return std::string(buffer);
}

std::ostream&
operator<<(std::ostream& stream, const Flow& f) 
{
    return stream << f.to_string();
}

uint64_t
Flow::hash_code() const
{
    unsigned char md[MD5_DIGEST_LENGTH];
    MD5_CTX ctx;
    MD5_Init(&ctx);
	MD5_Update(&ctx, &in_port, sizeof(in_port));
	MD5_Update(&ctx, &dl_vlan, sizeof(dl_vlan));
	MD5_Update(&ctx, &dl_vlan_pcp, sizeof(dl_vlan_pcp));
	MD5_Update(&ctx, &dl_src, sizeof(dl_src.octet));
	MD5_Update(&ctx, &dl_dst, sizeof(dl_dst.octet));
	MD5_Update(&ctx, &dl_type, sizeof(dl_type));
	MD5_Update(&ctx, &nw_src, sizeof(nw_src));
	MD5_Update(&ctx, &nw_dst, sizeof(nw_dst));
	MD5_Update(&ctx, &nw_proto, sizeof(nw_proto));
	MD5_Update(&ctx, &tp_src, sizeof(tp_src));
	MD5_Update(&ctx, &tp_dst, sizeof(tp_dst));
    MD5_Final(md, &ctx);

    return *((uint64_t*)md);
}

} // namespace vigil
