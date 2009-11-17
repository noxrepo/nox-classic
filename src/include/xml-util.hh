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
#ifndef XML_HH
#define XML_HH 1

#include <list>
#include <string>

#include <boost/scoped_array.hpp>

#include <xercesc/dom/DOM.hpp>

namespace vigil {
namespace xml {

/*
 * Xerces convenience functions component developers may find useful
 * while accessing a XML DOM tree passed for them.
 */

/* Transform a XML string into a standard string. */
inline 
std::string to_string(const XMLCh* s) {
    assert(s);
    boost::scoped_array<char> ptr(xercesc::XMLString::transcode(s));
    return std::string(ptr.get());
}

/* Compares a XML string and a standard string. */
inline
bool operator==(const XMLCh* x, const std::string& s) {
    return x && s == to_string(x);
}

/* Gets a single child of a given node based on its tag. If there's
 * more than a single child with the same tag, the first one is
 * returned. If nothing is found, 0 is returned.
 */
const xercesc::DOMNode* get_child_by_tag(const xercesc::DOMNode*, 
                                         const std::string&);

/* Gets all children of a given node based on their tag. If nothing is
 * found, an empty list is returned.
 */
const std::list<xercesc::DOMNode*> get_children_by_tag(const xercesc::DOMNode*, 
                                                       const std::string&);

/* Load a XML document. */
xercesc::DOMDocument* load_document(const std::string& schema, 
                                    const std::string& file,
                                    std::string& error);

}
}

#endif
