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
		      uint8_t type, uint16_t length)
  {
    header(of_raw, type, length, OFP_VERSION, 0);
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
