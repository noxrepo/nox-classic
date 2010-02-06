/** Copyright 2009 (C) Stanford University
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
#include "openflow-pack.hh"
#include "vlog.hh"
#include <time.h>
#include <stdlib.h>

namespace vigil
{
  static Vlog_module lg("openflow-pack");

  uint32_t ofpack::nextxid = OPENFLOW_PACK_MIN_XID;

  void ofp_action::set_action_nw_addr(uint16_t type, uint32_t ip)
  {
    action_raw.reset(new uint8_t[sizeof(ofp_action_nw_addr)]);
    header = (ofp_action_header*) action_raw.get();
    ofp_action_nw_addr* oana = (ofp_action_nw_addr*) header;
    
    oana->type = htons(type);
    oana->len = htons(sizeof(ofp_action_nw_addr));
    oana->nw_addr = htonl(ip);
  }

  void ofp_action::set_action_dl_addr(uint16_t type, ethernetaddr mac)
  {
    action_raw.reset(new uint8_t[sizeof(ofp_action_dl_addr)]);
    header = (ofp_action_header*) action_raw.get();
    ofp_action_dl_addr* oada = (ofp_action_dl_addr*) header;
    
    oada->type = htons(type);
    oada->len = htons(sizeof(ofp_action_dl_addr));
    memcpy(oada->dl_addr, mac.octet, ethernetaddr::LEN);
  }

  void ofp_action::set_action_enqueue(uint16_t port, uint32_t queueid)
  {
    action_raw.reset(new uint8_t[sizeof(ofp_action_enqueue)]);
    header = (ofp_action_header*) action_raw.get();
    ofp_action_enqueue* oae = (ofp_action_enqueue*) header;

    oae->type = htons(OFPAT_ENQUEUE);
    oae->len = htons(sizeof(ofp_action_enqueue));
    oae->port = htons(port);
    oae->queue_id = htonl(queueid);
  }

  void ofp_action::set_action_output(uint16_t port, uint16_t max_len)
  {
    action_raw.reset(new uint8_t[sizeof(ofp_action_output)]);
    header = (ofp_action_header*) action_raw.get();
    ofp_action_output* oao = (ofp_action_output*) header;
    
    oao->type = htons(OFPAT_OUTPUT);
    oao->len = htons(sizeof(ofp_action_output));
    oao->port = htons(port);
    oao->max_len = htons(max_len);
  }

  uint16_t ofp_action_list::mem_size()
  {
    uint16_t size = 0;
    std::list<ofp_action>::iterator i = action_list.begin();
    while (i != action_list.end())
    {
      size += ntohs(i->header->len);
      i++;
    }

    return size;
  }
  
  uint32_t ofpack::rand_uint32()
  {
    srand(time(NULL));
    uint32_t value = 0;
    uint8_t* currVal = (uint8_t*) &value;
    
    for (int i = 0; i < 4; i++)
    {
      *currVal = (uint8_t) rand()%256;
      currVal++;
    }
    return value;
  }

  uint32_t ofpack::get_xid()
  {
    uint32_t value;

    switch(OPENFLOW_PACK_XID_METHOD)
    {
    case OPENFLOW_PACK_XID_METHOD_RANDOM:
      while ((value = rand_uint32()) < OPENFLOW_PACK_MIN_XID);
      return value;
    case OPENFLOW_PACK_XID_METHOD_INCREMENT:
    default:
      if (nextxid == 0)
      {
	VLOG_INFO(lg, "OpenFlow transaction id wrapped around");
	nextxid = OPENFLOW_PACK_MIN_XID;
      }
      return nextxid++;
    }
  }

  uint32_t ofpack::header(boost::shared_array<uint8_t>& of_raw, 
			  uint8_t type, uint16_t length, uint8_t version)
  {
    header(of_raw, type, length, version, 0);
    return xid(of_raw);
  }
  
  void ofpack::header(boost::shared_array<uint8_t>& of_raw, uint8_t type,
		      uint16_t length, uint8_t version, uint32_t xid)
  {
    of_raw.reset(new uint8_t[length]);
    header(get_ofph(of_raw), type, length, version, xid);
  }
  
  void ofpack::header(ofp_header* ofph, uint8_t type,
		      uint16_t length, uint8_t version, uint32_t xid)
  {
    ofph->version = version;
    ofph->type = type;
    ofph->length = htons(length);
    ofph->xid = htonl(xid);
  }

  void ofpack::flow_mod(boost::shared_array<uint8_t>& of_raw, 
			ofp_action_list list)
  {
    header(of_raw, OFPT_FLOW_MOD, list.mem_size()+sizeof(ofp_flow_mod));
  }

  void ofpack::flow_mod_exact(boost::shared_array<uint8_t>& of_raw, 
			      const Flow& flow, uint32_t buffer_id, 
			      uint16_t in_port, uint16_t command, 
			      uint64_t cookie, uint16_t out_port,
			      uint16_t idle_timeout, uint16_t hard_timeout, 
			      uint16_t priority, uint32_t wildcards)
  {
    ofp_flow_mod* ofm = (ofp_flow_mod*) of_raw.get();
    ofm->cookie = htonll(cookie);
    ofm->command = htons(command);
    ofm->flags = htons(ofd_flow_mod_flags());
    ofm->idle_timeout = htons(idle_timeout);
    ofm->hard_timeout = htons(hard_timeout);
    ofm->priority = htons(priority);
    ofm->buffer_id = htonl(buffer_id);
    ofm->out_port = htons(out_port);

    ofp_match& match = ofm->match;
    match.wildcards = htonl(wildcards);
    match.in_port = in_port;
    memcpy(match.dl_src, flow.dl_src.octet, ethernetaddr::LEN);
    memcpy(match.dl_dst, flow.dl_dst.octet, ethernetaddr::LEN);
    match.dl_vlan = flow.dl_vlan;
    match.dl_vlan = flow.dl_vlan_pcp;
    match.pad1[0] = 0;
    match.dl_type = flow.dl_type;
    match.nw_tos = flow.nw_tos;
    match.nw_proto = flow.nw_proto;
    match.pad2[0] = match.pad2[1] = 0;
    match.nw_src = flow.nw_src;
    match.nw_dst = flow.nw_dst;
    match.tp_src = flow.tp_src;
    match.tp_dst = flow.tp_dst;
  }

  void ofpack::flow_mod_actions(boost::shared_array<uint8_t>& of_raw, 
				ofp_action_list list)
  {
    ofp_flow_mod* ofm = (ofp_flow_mod*) of_raw.get();
    uint8_t* actions = (uint8_t*) ofm->actions;

    std::list<ofp_action>::iterator i = list.action_list.begin();
    while (i != list.action_list.end())
    {
      memcpy(actions, i->header, ntohs(i->header->len));
      actions += ntohs(i->header->len);
      i++;
    }
  }

  void ofpack::stat_req(boost::shared_array<uint8_t>& of_raw,
			uint16_t type, uint16_t flags)
  {
    ofp_stats_request* osr = (ofp_stats_request*) of_raw.get();
    osr->type = htons(type);
    osr->flags = htons(flags);
  }

  void ofpack::port_stat_req(boost::shared_array<uint8_t>& of_raw,
			    uint16_t port, uint16_t flags)
  {
    header(of_raw, OFPT_STATS_REQUEST, sizeof(ofp_stats_request)+
	   sizeof(ofp_port_stats_request));
    stat_req(of_raw, OFPST_PORT,flags);
    
    ofp_stats_request* osr = (ofp_stats_request*) of_raw.get();
    ofp_port_stats_request* opsr = (ofp_port_stats_request*) osr->body;
    opsr->port_no = htons(port);
  }


  ofp_header ofupack::header(ofp_header* ofph)
  {
    ofp_header rofph;
    rofph.version = ofph->version;
    rofph.type = ofph->type;
    rofph.length = ntohs(ofph->length);
    rofph.xid = xid(ofph);
    return rofph;
  }


}// namespace vigil
