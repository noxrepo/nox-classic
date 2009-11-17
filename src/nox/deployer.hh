/* Copyright 2008, 2009 (C) Nicira, Inc.
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
#ifndef DEPLOYER_HH
#define DEPLOYER_HH 1

#include <list>
#include <string>

#include <boost/filesystem.hpp>

#include <xercesc/dom/DOM.hpp>

#include "component.hh"
#include "hash_map.hh"
#include "kernel.hh"

namespace vigil {

class Component_context;
class Component_configuration;

/* A deployer constructs a context and passes it for the kernel when
 * asked for.  NOX supports multiple deployers, and indeed, NOX has a
 * deployer for statically linked components, dynamically linked
 * components as well for components implemented in Python.
 */
class Deployer {
public:
    virtual ~Deployer();
    virtual bool deploy(Kernel*, const container::Component_name&);

    static const char* COMPONENTS_CONFIGURATION_SCHEMA;
    static const char* XML_DESCRIPTION;

    /* Find recursively any XML component description files. */
    typedef std::list<boost::filesystem::path> Path_list;
    static Path_list scan(boost::filesystem::path);

    /* Get all contexts the deployer knows about. */
    Component_context_list get_contexts() const;

protected:
    /* Components known about, but not installed into the kernel. */
    typedef hash_map<container::Component_name, 
                     Component_context*> Component_name_context_map;
    Component_name_context_map uninstalled_contexts;
};

/* An abstract component class for deployer implementations to use. */
class Component_configuration 
    : public container::Configuration {
public:
    Component_configuration();
    Component_configuration(xercesc::DOMNode*, 
                            const container::Component_argument_list&);
    const std::string get(const std::string&) const;
    const bool has(const std::string&) const;
    const std::list<std::string> keys() const;
    const container::Component_argument_list get_arguments() const;

    /* Human-readable component name */
    container::Component_name name;
    
    /* Component's XML description */
    xercesc::DOMNode* xml_description;

    /* Command line arguments */
    container::Component_argument_list arguments;

private:
    /* XML configuration translated into key-value pairs */
    mutable hash_map<std::string, std::string> kv;
};

}

#endif
