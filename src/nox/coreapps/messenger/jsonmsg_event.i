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
%{
#include "core_events.hh"
#include "jsonmessenger.hh"
#include "pyrt/pycontext.hh"
#include "pyrt/pyevent.hh"
#include "pyrt/pyglue.hh"

using namespace std;
using namespace vigil;
%}

%import(module="nox.coreapps.pyrt.pycomponent") "pyrt/event.i"

%include "common-defs.i"
%include "std_string.i"
%include "cstring.i"

%inline %{
struct JSON_reply
{
    Msg_stream * sock;
    JSON_reply ()
    {
    }
    void __call__ (char * msg)
    {
        sock->send(msg);
    }
};
%}

class JSONMsg_event
    : public Event
{
public:
    JSONMsg_event(const core_message* cmsg);
    
    ~JSONMsg_event()
    {}
    
    JSONMsg_event() : Event(static_get_name()) 
    { }

    static const Event_name static_get_name() 
    {
      return "JSONMsg_event";
    }

    Msg_stream* sock;

    boost::shared_ptr<json_object> jsonobj;
   
%pythoncode
%{
    def __str__(self):
        return 'JSONMsg_event jsonobj->get_string())'
%}

%extend {


    static void fill_python_event(const Event& e, PyObject* proxy) 
    {
        const JSONMsg_event& jme = dynamic_cast<const JSONMsg_event&>(e);
        pyglue_setattr_string(proxy, "jsonstring",
                            to_python(jme.jsonobj->get_string()));
        static PyObject * reply_ctor;
        if (!reply_ctor)
        {
            PyObject* pname = PyString_FromString("nox.coreapps.messenger.pyjsonmsgevent");
            if (!pname) {
                throw runtime_error("unable to create a module string");
            }

            PyObject* pmod = PyImport_Import(pname);
            if (!pmod || !PyModule_Check(pmod)){
                Py_DECREF(pname);
                Py_XDECREF(pmod);
                throw runtime_error("unable to import json messenger module");
            }
            Py_DECREF(pname);

            reply_ctor = PyObject_GetAttrString(pmod, (char*)"JSON_reply");
            if (!reply_ctor || !PyCallable_Check(reply_ctor)) {
                Py_DECREF(pmod);
                Py_XDECREF(reply_ctor);
                throw runtime_error("unable to pull in a pyevent constructor");
            }
            Py_DECREF(pmod);
        }
        PyObject* reply = PyObject_CallObject(reply_ctor, 0);
        if (!reply) {
            throw runtime_error("unable to create json_reply");
        }
        ((JSON_reply*)(SWIG_Python_GetSwigThis(reply)->ptr))->sock = jme.sock;
        pyglue_setattr_string(proxy, "reply", reply);

        ((Event*)SWIG_Python_GetSwigThis(proxy)->ptr)->operator=(e);
    }

    static void register_event_converter(PyObject *ctxt) {
        if (!SWIG_Python_GetSwigThis(ctxt) || 
            !SWIG_Python_GetSwigThis(ctxt)->ptr) {
            throw std::runtime_error("Unable to access Python context.");
        }
        
        vigil::applications::PyContext* pyctxt = 
            (vigil::applications::PyContext*)SWIG_Python_GetSwigThis(ctxt)->ptr;
        pyctxt->register_event_converter<JSONMsg_event>
            (&JSONMsg_event_fill_python_event);
    }
};

};
