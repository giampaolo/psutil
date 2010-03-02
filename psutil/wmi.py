"""
Windows Management Instrumentation (WMI) is Microsoft's answer to
the DMTF's Common Information Model. It allows you to query just
about any conceivable piece of information from any computer which
is running the necessary agent and over which have you the
necessary authority.

Since the COM implementation doesn't give much away to Python
programmers, I've wrapped it in some lightweight classes with
some getattr / setattr magic to ease the way. In particular:

* The :class:`_wmi_namespace` object itself will determine its classes
  and allow you to return all instances of any of them by
  using its name as an attribute::

    disks = wmi.WMI ().Win32_LogicalDisk ()

* In addition, you can specify what would become the WHERE clause
  as keyword parameters::

    fixed_disks = wmi.WMI ().Win32_LogicalDisk (DriveType=3)

* The objects returned by a WMI lookup are wrapped in a Python
  class which determines their methods and classes and allows
  you to access them as though they were Python classes. The
  methods only allow named parameters::

    for p in wmi.WMI ().Win32_Process (Name="notepad.exe"):
      p.Terminate (Result=1)

* Doing a print on one of the WMI objects will result in its
  `GetObjectText\_` method being called, which usually produces
  a meaningful printout of current values.
  The repr of the object will include its full WMI path,
  which lets you get directly to it if you need to.

* You can get the associators and references of an object as
  a list of python objects by calling the associators () and
  references () methods on a WMI Python object::

    for p in wmi.WMI ().Win32_Process (Name="notepad.exe"):
      for r in p.references ():
        print r

  ..  note::
      Don't do this on a Win32_ComputerSystem object; it will
      take all day and kill your machine!


* WMI classes (as opposed to instances) are first-class
  objects, so you can get hold of a class, and call
  its methods or set up a watch against it::

    process = wmi.WMI ().Win32_Process
    process.Create (CommandLine="notepad.exe")

* To make it easier to use in embedded systems and py2exe-style
  executable wrappers, the module will not force early Dispatch.
  To do this, it uses a handy hack by Thomas Heller for easy access
  to constants.

Typical usage will be::

  import wmi

  vodev1 = wmi.WMI ("vodev1")
  for disk in vodev1.Win32_LogicalDisk ():
    if disk.DriveType == 3:
      space = 100 * long (disk.FreeSpace) / long (disk.Size)
      print "%s has %d%% free" % (disk.Name, space)

Many thanks, obviously to Mark Hammond for creating the win32all
extensions, but also to Alex Martelli and Roger Upole, whose
c.l.py postings pointed me in the right direction.
Thanks especially in release 1.2 to Paul Tiemann for his code
contributions and robust testing.
"""
__VERSION__ = __version__ = "1.4.6"

_DEBUG = False

import sys
import datetime
import re
import struct
import warnings

from win32com.client import GetObject, Dispatch
import pywintypes

def signed_to_unsigned (signed):
  """Convert a (possibly signed) long to unsigned hex. Useful
  when converting a COM error code to the more conventional
  8-digit hex::

    print "%08X" % signed_to_unsigned (-2147023174)
  """
  unsigned, = struct.unpack ("L", struct.pack ("l", signed))
  return unsigned

class SelfDeprecatingDict (object):
  """Provides for graceful degradation of objects which
  are currently dictionaries (and therefore accessed via
  `.keys`, `.items`, etc.) into lists. Wraps an existing
  `dict` and allows it to be addressed as a `dict` or as a
  `list` during an interregnum, issuing a `DeprecationWarning`
  if accessed as a `dict`.
  """

  dict_only = set (dir (dict)).difference (dir (list))

  def __init__ (self, dictlike):
    self.dict = dict (dictlike)
    self.list = list (self.dict)

  def __getattr__ (self, attribute):
    if attribute in self.dict_only:
      warnings.warn ("In future this will be a list and not a dictionary", DeprecationWarning)
      return getattr (self.dict, attribute)
    else:
      return getattr (self.list, attribute)

  def __iter__ (self):
    return iter (self.list)

  def __str__ (self):
    return str (self.list)

  def __repr__ (self):
    return repr (self.list)

  def __getitem__ (self, item):
    try:
      return self.list[item]
    except TypeError:
      return self.dict[item]

class ProvideConstants (object):
  """When called on a ``win32com.client.Dispatch`` object,
  provides lazy access to constants defined in the typelib.
  They can then be accessed as attributes of the :attr:`_constants`
  property. (From Thomas Heller on c.l.py).
  """
  def __init__(self, comobj):
    comobj.__dict__["_constants"] = self
    self.__typecomp = \
    comobj._oleobj_.GetTypeInfo().GetContainingTypeLib()[0].GetTypeComp()

  def __getattr__(self, name):
    if name.startswith("__") and name.endswith("__"):
     raise AttributeError (name)
    result = self.__typecomp.Bind(name)
    if not result[0]:
     raise AttributeError (name)
    return result[1].value

obj = GetObject ("winmgmts:")
ProvideConstants (obj)

wbemErrInvalidQuery = obj._constants.wbemErrInvalidQuery
wbemErrTimedout = obj._constants.wbemErrTimedout
wbemFlagReturnImmediately = obj._constants.wbemFlagReturnImmediately
wbemFlagForwardOnly = obj._constants.wbemFlagForwardOnly

#
# Exceptions
#
class x_wmi (Exception):
  """Ancestor of all wmi-related exceptions. Keeps track of
  an info message and the underlying COM error if any, exposed
  as the :attr:`com_error` attribute.
  """
  def __init__ (self, info="", com_error=None):
    self.info = info
    self.com_error = com_error

  def __str__ (self):
    return "<x_wmi: %s %s>" % (
      self.info or "Unexpected COM Error",
      self.com_error or "(no underlying exception)"
    )

class x_wmi_invalid_query (x_wmi):
  "Raised when a WMI returns `wbemErrInvalidQuery`"
  pass

class x_wmi_timed_out (x_wmi):
  "Raised when a watcher times out"
  pass

class x_wmi_no_namespace (x_wmi):
  """Raised when an attempt is made to query or watch
  from a class without a namespace.
  """
  pass

class x_access_denied (x_wmi):
  "Raised when WMI raises 80070005"
  pass

class x_wmi_authentication (x_wmi):
  "Raised when an invalid combination of authentication properties is attempted when connecting"
  pass

class x_wmi_uninitialised_thread (x_wmi):
  """Raised when WMI returns 800401E4 on connection, usually
  indicating that no COM threading model has been initialised
  """
  pass

WMI_EXCEPTIONS = {
  signed_to_unsigned (wbemErrInvalidQuery) : x_wmi_invalid_query,
  signed_to_unsigned (wbemErrTimedout) : x_wmi_timed_out,
  0x80070005 : x_access_denied,
  0x80041003 : x_access_denied,
  0x800401E4 : x_wmi_uninitialised_thread,
}

def handle_com_error (err=None):
  """Convenience wrapper for displaying all manner of COM errors.
  Raises a :exc:`x_wmi` exception with more useful information attached

  :param err: The structure attached to a `pywintypes.com_error`
  """
  if err is None:
    _, err, _ = sys.exc_info ()
  hresult_code, hresult_name, additional_info, parameter_in_error = err.args
  hresult_code = signed_to_unsigned (hresult_code)
  exception_string = ["%s - %s" % (hex (hresult_code), hresult_name)]
  scode = None
  if additional_info:
    wcode, source_of_error, error_description, whlp_file, whlp_context, scode = additional_info
    scode = signed_to_unsigned (scode)
    exception_string.append ("  Error in: %s" % source_of_error)
    exception_string.append ("  %s - %s" % (hex (scode), (error_description or "").strip ()))
  for error_code, klass in WMI_EXCEPTIONS.items ():
    if error_code in (hresult_code, scode):
      break
  else:
    klass = x_wmi
  raise klass (com_error=err)


BASE = datetime.datetime (1601, 1, 1)
def from_1601 (ns100):
  return BASE + datetime.timedelta (microseconds=int (ns100) / 10)

def from_time (year=None, month=None, day=None, hours=None, minutes=None, seconds=None, microseconds=None, timezone=None):
  """Convenience wrapper to take a series of date/time elements and return a WMI time
  of the form `yyyymmddHHMMSS.mmmmmm+UUU`. All elements may be int, string or
  omitted altogether. If omitted, they will be replaced in the output string
  by a series of stars of the appropriate length.

  :param year: The year element of the date/time
  :param month: The month element of the date/time
  :param day: The day element of the date/time
  :param hours: The hours element of the date/time
  :param minutes: The minutes element of the date/time
  :param seconds: The seconds element of the date/time
  :param microseconds: The microseconds element of the date/time
  :param timezone: The timeezone element of the date/time

  :returns: A WMI datetime string of the form: `yyyymmddHHMMSS.mmmmmm+UUU`
  """
  def str_or_stars (i, length):
    if i is None:
      return "*" * length
    else:
      return str (i).rjust (length, "0")

  wmi_time = ""
  wmi_time += str_or_stars (year, 4)
  wmi_time += str_or_stars (month, 2)
  wmi_time += str_or_stars (day, 2)
  wmi_time += str_or_stars (hours, 2)
  wmi_time += str_or_stars (minutes, 2)
  wmi_time += str_or_stars (seconds, 2)
  wmi_time += "."
  wmi_time += str_or_stars (microseconds, 6)
  wmi_time += "+"
  wmi_time += str_or_stars (timezone, 3)

  return wmi_time

def to_time (wmi_time):
  """Convenience wrapper to take a WMI datetime string of the form
  yyyymmddHHMMSS.mmmmmm+UUU and return a 9-tuple containing the
  individual elements, or None where string contains placeholder
  stars.

  :param wmi_time: The WMI datetime string in `yyyymmddHHMMSS.mmmmmm+UUU` format

  :returns: A 9-tuple of (year, month, day, hours, minutes, seconds, microseconds, timezone)
  """
  def int_or_none (s, start, end):
    try:
      return int (s[start:end])
    except ValueError:
      return None

  year = int_or_none (wmi_time, 0, 4)
  month = int_or_none (wmi_time, 4, 6)
  day = int_or_none (wmi_time, 6, 8)
  hours = int_or_none (wmi_time, 8, 10)
  minutes = int_or_none (wmi_time, 10, 12)
  seconds = int_or_none (wmi_time, 12, 14)
  microseconds = int_or_none (wmi_time, 15, 21)
  timezone = wmi_time[22:]
  if timezone == "***":
    timezone = None

  return year, month, day, hours, minutes, seconds, microseconds, timezone

def _set (obj, attribute, value):
  """Helper function to add an attribute directly into the instance
  dictionary, bypassing possible `__getattr__` calls

  :param obj: Any python object
  :param attribute: String containing attribute name
  :param value: Any python object
  """
  obj.__dict__[attribute] = value

class _wmi_method:
  """A currying sort of wrapper around a WMI method name. It
  abstract's the method's parameters and can be called like
  a normal Python object passing in the parameter values.

  Output parameters are returned from the call as a tuple.
  In addition, the docstring is set up as the method's
  signature, including an indication as to whether any
  given parameter is expecting an array, and what
  special privileges are required to call the method.
  """

  def __init__ (self, ole_object, method_name):
    """
    :param ole_object: The WMI class/instance whose method is to be called
    :param method_name: The name of the method to be called
    """
    try:
      self.ole_object = Dispatch (ole_object)
      self.method = ole_object.Methods_ (method_name)
      self.qualifiers = {}
      for q in self.method.Qualifiers_:
        self.qualifiers[q.Name] = q.Value
      self.provenance = "\n".join (self.qualifiers.get ("MappingStrings", []))

      self.in_parameters = self.method.InParameters
      self.out_parameters = self.method.OutParameters
      if self.in_parameters is None:
        self.in_parameter_names = []
      else:
        self.in_parameter_names = [(i.Name, i.IsArray) for i in self.in_parameters.Properties_]
      if self.out_parameters is None:
        self.out_parameter_names = []
      else:
        self.out_parameter_names = [(i.Name, i.IsArray) for i in self.out_parameters.Properties_]

      doc = "%s (%s) => (%s)" % (
        method_name,
        ", ".join ([name + ("", "[]")[is_array] for (name, is_array) in self.in_parameter_names]),
        ", ".join ([name + ("", "[]")[is_array] for (name, is_array) in self.out_parameter_names])
      )
      privileges = self.qualifiers.get ("Privileges", [])
      if privileges:
        doc += " | Needs: " + ", ".join (privileges)
      self.__doc__ = doc
    except pywintypes.com_error:
      handle_com_error ()

  def __call__ (self, *args, **kwargs):
    """Execute the call to a WMI method, returning
    a tuple (even if is of only one value) containing
    the out and return parameters.
    """
    try:
      if self.in_parameters:
        parameter_names = {}
        for name, is_array in self.in_parameter_names:
          parameter_names[name] = is_array

        parameters = self.in_parameters

        #
        # Check positional parameters first
        #
        for n_arg in range (len (args)):
          arg = args[n_arg]
          parameter = parameters.Properties_[n_arg]
          if parameter.IsArray:
            try: list (arg)
            except TypeError: raise TypeError ("parameter %d must be iterable" % n_arg)
          parameter.Value = arg

        #
        # If any keyword param supersedes a positional one,
        # it'll simply overwrite it.
        #
        for k, v in kwargs.items ():
          is_array = parameter_names.get (k)
          if is_array is None:
            raise AttributeError ("%s is not a valid parameter for %s" % (k, self.__doc__))
          else:
            if is_array:
              try: list (v)
              except TypeError: raise TypeError ("%s must be iterable" % k)
          parameters.Properties_ (k).Value = v

        result = self.ole_object.ExecMethod_ (self.method.Name, self.in_parameters)
      else:
        result = self.ole_object.ExecMethod_ (self.method.Name)

      results = []
      for name, is_array in self.out_parameter_names:
        value = result.Properties_ (name).Value
        if is_array:
          #
          # Thanks to Jonas Bjering for bug report and patch
          #
          results.append (list (value or []))
        else:
          results.append (value)
      return tuple (results)

    except pywintypes.com_error:
      handle_com_error ()

  def __repr__ (self):
    return "<function %s>" % self.__doc__

class _wmi_property (object):

  def __init__ (self, property):
    self.property = property
    self.name = property.Name
    self.value = property.Value
    self.qualifiers = dict ((q.Name, q.Value) for q in property.Qualifiers_)
    self.type = self.qualifiers.get ("CIMTYPE", None)

  def set (self, value):
    self.property.Value = value

  def __getattr__ (self, attr):
    return getattr (self.property, attr)

#
# class _wmi_object
#
class _wmi_object:
  """The heart of the WMI module: wraps the objects returned by COM
  ISWbemObject interface and provide readier access to their properties
  and methods resulting in a more Pythonic interface. Not usually
  instantiated directly, rather as a result of calling a :class:`_wmi_class`
  on the parent :class:`_wmi_namespace`.

  If you get hold of a WMI-related COM object from some other
  source than this module, you can wrap it in one of these objects
  to get the benefits of the module::

    import win32com.client
    import wmi

    wmiobj = win32com.client.GetObject ("winmgmts:Win32_LogicalDisk.DeviceID='C:'")
    c_drive = wmi._wmi_object (wmiobj)
    print c_drive
  """

  def __init__ (self, ole_object, instance_of=None, fields=[], property_map={}):
    try:
      _set (self, "ole_object", ole_object)
      _set (self, "id", ole_object.Path_.DisplayName.lower ())
      _set (self, "_instance_of", instance_of)
      _set (self, "properties", {})
      _set (self, "methods", {})
      _set (self, "property_map", property_map)
      _set (self, "_associated_classes", None)
      _set (self, "_keys", None)

      if fields:
        for field in fields:
          self.properties[field] = None
      else:
        for p in ole_object.Properties_:
          self.properties[p.Name] = None

      for m in ole_object.Methods_:
        self.methods[m.Name] = None

      _set (self, "_properties", self.properties.keys ())
      _set (self, "_methods", self.methods.keys ())
      _set (self, "qualifiers", dict ((q.Name, q.Value) for q in self.ole_object.Qualifiers_))

    except pywintypes.com_error:
      handle_com_error ()

  def __lt__ (self, other):
    return self.id < other.id

  def __str__ (self):
    """For a call to print [object] return the OLE description
    of the properties / values of the object
    """
    try:
      return self.ole_object.GetObjectText_ ()
    except pywintypes.com_error:
      handle_com_error ()

  def __repr__ (self):
    """
    Indicate both the fact that this is a wrapped WMI object
    and the WMI object's own identifying class.
    """
    try:
      return "<%s: %s>" % (self.__class__.__name__, str (self.Path_.Path))
    except pywintypes.com_error:
      handle_com_error ()

  def _cached_properties (self, attribute):
    if self.properties[attribute] is None:
      self.properties[attribute] = _wmi_property (self.ole_object.Properties_ (attribute))
    return self.properties[attribute]

  def _cached_methods (self, attribute):
    if self.methods[attribute] is None:
      self.methods[attribute] = _wmi_method (self.ole_object, attribute)
    return self.methods[attribute]

  def __getattr__ (self, attribute):
    """
    Attempt to pass attribute calls to the proxied COM object.
    If the attribute is recognised as a property, return its value;
    if it is recognised as a method, return a method wrapper which
    can then be called with parameters; otherwise pass the lookup
    on to the underlying object.
    """
    try:
      if attribute in self.properties:
        property = self._cached_properties (attribute)
        factory = self.property_map.get (attribute, self.property_map.get (property.type, lambda x: x))
        value = factory (property.value)
        #
        # If this is an association, certain of its properties
        # are actually the paths to the aspects of the association,
        # so translate them automatically into WMI objects.
        #
        if property.type.startswith ("ref:"):
          return WMI (moniker=value)
        else:
          return value
      elif attribute in self.methods:
        return self._cached_methods (attribute)
      else:
        return getattr (self.ole_object, attribute)
    except pywintypes.com_error:
      handle_com_error ()

  def __setattr__ (self, attribute, value):
    """If the attribute to be set is valid for the proxied
    COM object, set that objects's parameter value; if not,
    raise an exception.
    """
    try:
      if attribute in self.properties:
        self._cached_properties (attribute).set (value)
        if self.ole_object.Path_.Path:
          self.ole_object.Put_ ()
      else:
        raise AttributeError (attribute)
    except pywintypes.com_error:
      handle_com_error ()

  def __eq__ (self, other):
    return self.id == other.id

  def __hash__ (self):
    return hash (self.id)

  def _getAttributeNames (self):
     """Return list of methods/properties for IPython completion"""
     attribs = [str (x) for x in self.methods.keys ()]
     attribs.extend ([str (x) for x in self.properties.keys ()])
     return attribs

  def _get_keys (self):
    """A WMI object is uniquely defined by a set of properties
    which constitute its keys. Lazily retrieves the keys for this
    instance or class.

    :returns: list of key property names
    """
    # NB You can get the keys of an instance more directly, via
    # Path\_.Keys but this doesn't apply to classes. The technique
    # here appears to work for both.
    if self._keys is None:
      _set (self, "_keys", [])
      for property in self.ole_object.Properties_:
        for qualifier in property.Qualifiers_:
          if qualifier.Name == "key" and qualifier.Value:
            self._keys.append (property.Name)
    return self._keys
  keys = property (_get_keys)

  def put (self):
    """Push all outstanding property updates back to the
    WMI database.
    """
    self.ole_object.Put_ ()

  def set (self, **kwargs):
    """Set several properties of the underlying object
    at one go. This is particularly useful in combination
    with the new () method below. However, an instance
    which has been spawned in this way won't have enough
    information to write pack, so only try if the
    instance has a path.
    """
    if kwargs:
      try:
        for attribute, value in kwargs.items ():
          if attribute in self.properties:
            self._cached_properties (attribute).set (value)
          else:
            raise AttributeError (attribute)
        #
        # Only try to write the attributes
        #  back if the object exists.
        #
        if self.ole_object.Path_.Path:
          self.ole_object.Put_ ()
      except pywintypes.com_error:
        handle_com_error ()

  def path (self):
    """Return the WMI URI to this object. Can be used to
    determine the path relative to the parent namespace::

      pp0 = wmi.WMI ().Win32_ParallelPort ()[0]
      print pp0.path ().RelPath

    ..  Do more with this
    """
    try:
      return self.ole_object.Path_
    except pywintypes.com_error:
      handle_com_error ()

  def derivation (self):
    """Return a tuple representing the object derivation for
    this object, with the most specific object first::

      pp0 = wmi.WMI ().Win32_ParallelPort ()[0]
      print ' <- '.join (pp0.derivation ())
    """
    try:
      return self.ole_object.Derivation_
    except pywintypes.com_error:
      handle_com_error ()

  def _cached_associated_classes (self):
    if self._associated_classes is None:
      if isinstance (self, _wmi_class):
        params = {'bSchemaOnly' : True}
      else:
        params = {'bClassesOnly' : True}
      try:
        associated_classes = dict (
          (assoc.Path_.Class, _wmi_class (self._namespace, assoc)) for
            assoc in self.ole_object.Associators_ (**params)
        )
        _set (self, "_associated_classes", associated_classes)
      except pywintypes.com_error:
        handle_com_error ()

    return self._associated_classes
  associated_classes = property (_cached_associated_classes)

  def associators (self, wmi_association_class="", wmi_result_class=""):
    """Return a list of objects related to this one, optionally limited
    either by association class (ie the name of the class which relates
    them) or by result class (ie the name of the class which would be
    retrieved)::

      c = wmi.WMI ()
      pp = c.Win32_ParallelPort ()[0]

      for i in pp.associators (wmi_association_class="Win32_PortResource"):
        print i

      for i in pp.associators (wmi_result_class="Win32_PnPEntity"):
        print i
    """
    try:
      return [
        _wmi_object (i) for i in \
          self.ole_object.Associators_ (
           strAssocClass=wmi_association_class,
           strResultClass=wmi_result_class
         )
      ]
    except pywintypes.com_error:
      handle_com_error ()

  def references (self, wmi_class=""):
    """Return a list of associations involving this object, optionally
    limited by the result class (the name of the association class).

    NB Associations are treated specially; although WMI only returns
    the string corresponding to the instance of each associated object,
    this module will automatically convert that to the object itself::

      c =  wmi.WMI ()
      sp = c.Win32_SerialPort ()[0]

      for i in sp.references ():
        print i

      for i in sp.references (wmi_class="Win32_SerialPortSetting"):
        print i
    """
    #
    # FIXME: Allow an actual class to be passed in, using
    # its .Path_.RelPath property to determine the string
    #
    try:
      return [_wmi_object (i) for i in self.ole_object.References_ (strResultClass=wmi_class)]
    except pywintypes.com_error:
      handle_com_error ()

#
# class _wmi_event
#
class _wmi_event (_wmi_object):
  """Slight extension of the _wmi_object class to allow
  objects which are the result of events firing to return
  extra information such as the type of event.
  """
  event_type_re = re.compile ("__Instance(Creation|Modification|Deletion)Event")
  def __init__ (self, event, event_info, fields=[]):
    _wmi_object.__init__ (self, event, fields=fields)
    _set (self, "event_type", None)
    _set (self, "timestamp", None)
    _set (self, "previous", None)

    if event_info:
      event_type = self.event_type_re.match (event_info.Path_.Class).group (1).lower ()
      _set (self, "event_type", event_type)
      if hasattr (event_info, "TIME_CREATED"):
        _set (self, "timestamp", from_1601 (event_info.TIME_CREATED))
      if hasattr (event_info, "PreviousInstance"):
        _set (self, "previous", event_info.PreviousInstance)

#
# class _wmi_class
#
class _wmi_class (_wmi_object):
  """Currying class to assist in issuing queries against
   a WMI namespace. The idea is that when someone issues
   an otherwise unknown method against the WMI object, if
   it matches a known WMI class a query object will be
   returned which may then be called with one or more params
   which will form the WHERE clause::

    c = wmi.WMI ()
    c_drives = c.Win32_LogicalDisk (Name='C:')
  """
  def __init__ (self, namespace, wmi_class):
    _wmi_object.__init__ (self, wmi_class)
    _set (self, "_class_name", wmi_class.Path_.Class)
    if namespace:
      _set (self, "_namespace", namespace)
    else:
      class_moniker = wmi_class.Path_.DisplayName
      winmgmts, namespace_moniker, class_name = class_moniker.split (":")
      namespace = _wmi_namespace (GetObject (winmgmts + ":" + namespace_moniker), False)
      _set (self, "_namespace", namespace)

  def query (self, fields=[], **where_clause):
    """Make it slightly easier to query against the class,
     by calling the namespace's query with the class preset.
     Won't work if the class has been instantiated directly.
    """
    #
    # FIXME: Not clear if this can ever happen
    #
    if self._namespace is None:
      raise x_wmi_no_namespace ("You cannot query directly from a WMI class")

    try:
      field_list = ", ".join (fields) or "*"
      wql = "SELECT " + field_list + " FROM " + self._class_name
      if where_clause:
        wql += " WHERE " + " AND ". join (["%s = '%s'" % (k, v) for k, v in where_clause.items ()])
      return self._namespace.query (wql, self, fields)
    except pywintypes.com_error:
      handle_com_error ()

  __call__ = query

  def watch_for (
    self,
    notification_type="operation",
    delay_secs=1,
    fields=[],
    **where_clause
  ):
    if self._namespace is None:
      raise x_wmi_no_namespace ("You cannot watch directly from a WMI class")

    valid_notification_types = ("operation", "creation", "deletion", "modification")
    if notification_type.lower () not in valid_notification_types:
      raise x_wmi ("notification_type must be one of %s" % ", ".join (valid_notification_types))

    return self._namespace.watch_for (
      notification_type=notification_type,
      wmi_class=self,
      delay_secs=delay_secs,
      fields=fields,
      **where_clause
    )

  def instances (self):
    """Return a list of instances of the WMI class
    """
    try:
      return [_wmi_object (instance, self) for instance in self.Instances_ ()]
    except pywintypes.com_error:
      handle_com_error ()

  def new (self, **kwargs):
    """This is the equivalent to the raw-WMI SpawnInstance\_
    method. Note that there are relatively few uses for
    this, certainly fewer than you might imagine. Most
    classes which need to create a new *real* instance
    of themselves, eg Win32_Process, offer a .Create
    method. SpawnInstance\_ is generally reserved for
    instances which are passed as parameters to such
    `.Create` methods, a common example being the
    `Win32_SecurityDescriptor`, passed to `Win32_Share.Create`
    and other instances which need security.

    The example here is `Win32_ProcessStartup`, which
    controls the shown/hidden state etc. of a new
    `Win32_Process` instance::

      import win32con
      import wmi
      c = wmi.WMI ()
      startup = c.Win32_ProcessStartup.new (ShowWindow=win32con.SW_SHOWMINIMIZED)
      pid, retval = c.Win32_Process.Create (
        CommandLine="notepad.exe",
        ProcessStartupInformation=startup
      )

    ..  warning::
        previous versions of this docstring illustrated using this function
        to create a new process. This is *not* a good example of its use;
        it is better handled with something like the example above.
    """
    try:
      obj = _wmi_object (self.SpawnInstance_ (), self)
      obj.set (**kwargs)
      return obj
    except pywintypes.com_error:
      handle_com_error ()

#
# class _wmi_result
#
class _wmi_result:
  """Simple, data only result for targeted WMI queries which request
  data only result classes via fetch_as_classes.
  """
  def __init__(self, obj, attributes):
    if attributes:
      for attr in attributes:
        self.__dict__[attr] = obj.Properties_ (attr).Value
    else:
      for p in obj.Properties_:
        attr = p.Name
        self.__dict__[attr] = obj.Properties_(attr).Value

#
# class WMI
#
class _wmi_namespace:
  """A WMI root of a computer system. The classes attribute holds a list
  of the classes on offer. This means you can explore a bit with
  things like this::

    c = wmi.WMI ()
    for i in c.classes:
      if "user" in i.lower ():
        print i
  """
  def __init__ (self, namespace, find_classes):
    _set (self, "_namespace", namespace)
    #
    # wmi attribute preserved for backwards compatibility
    #
    _set (self, "wmi", namespace)

    self._classes = None
    self._classes_map = {}
    #
    # Pick up the list of classes under this namespace
    #  so that they can be queried, and used as though
    #  properties of the namespace by means of the __getattr__
    #  hook below.
    # If the namespace does not support SubclassesOf, carry on
    #  regardless
    #
    if find_classes:
      _ = self.classes

  def __repr__ (self):
    return "<_wmi_namespace: %s>" % self.wmi

  def __str__ (self):
    return repr (self)

  def _get_classes (self):
    if self._classes is None:
      self._classes = self.subclasses_of ()
    return SelfDeprecatingDict (dict.fromkeys (self._classes))
  classes = property (_get_classes)

  def get (self, moniker):
    try:
      return _wmi_object (self.wmi.Get (moniker))
    except pywintypes.com_error:
      handle_com_error ()

  def handle (self):
    """The raw OLE object representing the WMI namespace"""
    return self._namespace

  def subclasses_of (self, root="", regex=r".*"):
    try:
      SubclassesOf = self._namespace.SubclassesOf
    except AttributeError:
      return set ()
    else:
      return set (
        c.Path_.Class
          for c in SubclassesOf (root)
          if re.match (regex, c.Path_.Class)
      )

  def instances (self, class_name):
    """Return a list of instances of the WMI class. This is
    (probably) equivalent to querying with no qualifiers::

      wmi.WMI ().instances ("Win32_LogicalDisk")
      # should be the same as
      wmi.WMI ().Win32_LogicalDisk ()
    """
    try:
      return [_wmi_object (obj) for obj in self._namespace.InstancesOf (class_name)]
    except pywintypes.com_error:
      handle_com_error ()

  def new (self, wmi_class, **kwargs):
    """This is now implemented by a call to :meth:`_wmi_class.new`"""
    return getattr (self, wmi_class).new (**kwargs)

  new_instance_of = new

  def _raw_query (self, wql):
    """Execute a WQL query and return its raw results.  Use the flags
    recommended by Microsoft to achieve a read-only, semi-synchronous
    query where the time is taken while looping through.
    NB Backslashes need to be doubled up.
    """
    flags = wbemFlagReturnImmediately | wbemFlagForwardOnly
    wql = wql.replace ("\\", "\\\\")
    try:
      return self._namespace.ExecQuery (strQuery=wql, iFlags=flags)
    except pywintypes.com_error:
      handle_com_error ()

  def query (self, wql, instance_of=None, fields=[]):
    """Perform an arbitrary query against a WMI object, and return
    a list of _wmi_object representations of the results.
    """
    return [ _wmi_object (obj, instance_of, fields) for obj in self._raw_query(wql) ]

  def fetch_as_classes (self, wmi_classname, fields=(), **where_clause):
    """Build and execute a wql query to fetch the specified list of fields from
    the specified wmi_classname + where_clause, then return the results as
    a list of simple class instances with attributes matching field_list.

    If fields is left empty, select * and pre-load all class attributes for
    each class returned.
    """
    wql = "SELECT %s FROM %s" % (fields and ", ".join (fields) or "*", wmi_classname)
    if where_clause:
      wql += " WHERE " + " AND ".join (["%s = '%s'" % (k, v) for k, v in where_clause.items()])
    return [_wmi_result (obj, fields) for obj in self._raw_query(wql)]

  def fetch_as_lists (self, wmi_classname, fields, **where_clause):
    """Build and execute a wql query to fetch the specified list of fields from
    the specified wmi_classname + where_clause, then return the results as
    a list of lists whose values correspond to field_list.
    """
    wql = "SELECT %s FROM %s" % (", ".join (fields), wmi_classname)
    if where_clause:
      wql += " WHERE " + " AND ".join (["%s = '%s'" % (k, v) for k, v in where_clause.items()])
    results = []
    for obj in self._raw_query(wql):
        results.append ([obj.Properties_ (field).Value for field in fields])
    return results

  def watch_for (
    self,
    raw_wql=None,
    notification_type="operation",
    wmi_class=None,
    delay_secs=1,
    fields=[],
    **where_clause
  ):
    """Set up an event tracker on a WMI event. This function
    returns an wmi_watcher which can be called to get the
    next event::

      c = wmi.WMI ()

      raw_wql = "SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_Process'"
      watcher = c.watch_for (raw_wql=raw_wql)
      while 1:
        process_created = watcher ()
        print process_created.Name

      # or

      watcher = c.watch_for (
        notification_type="Creation",
        wmi_class="Win32_Process",
        delay_secs=2,
        Name='calc.exe'
      )
      calc_created = watcher ()

    Now supports timeout on the call to watcher::

      import pythoncom
      import wmi
      c = wmi.WMI (privileges=["Security"])
      watcher1 = c.watch_for (
        notification_type="Creation",
        wmi_class="Win32_NTLogEvent",
        Type="error"
      )
      watcher2 = c.watch_for (
        notification_type="Creation",
        wmi_class="Win32_NTLogEvent",
        Type="warning"
      )

      while 1:
        try:
          error_log = watcher1 (500)
        except wmi.x_wmi_timed_out:
          pythoncom.PumpWaitingMessages ()
        else:
          print error_log

        try:
          warning_log = watcher2 (500)
        except wmi.x_wmi_timed_out:
          pythoncom.PumpWaitingMessages ()
        else:
          print warning_log
    """
    if isinstance (wmi_class, _wmi_class):
      class_name = wmi_class._class_name
    else:
      class_name = wmi_class
      wmi_class = getattr (self, class_name)
    is_extrinsic = "__ExtrinsicEvent" in wmi_class.derivation ()
    if raw_wql:
      wql = raw_wql
    else:
      fields = set (['TargetInstance'] + fields)
      field_list = ", ".join (fields) or "*"
      if is_extrinsic:
        if where_clause:
          where = " WHERE " + " AND ".join (["%s = '%s'" % (k, v) for k, v in where_clause.items ()])
        else:
          where = ""
        wql = "SELECT " + field_list + " FROM " + class_name + where
      else:
        if where_clause:
          where = " AND " + " AND ".join (["TargetInstance.%s = '%s'" % (k, v) for k, v in where_clause.items ()])
        else:
          where = ""
        wql = \
          "SELECT %s FROM __Instance%sEvent WITHIN %d WHERE TargetInstance ISA '%s' %s" % \
          (field_list, notification_type, delay_secs, class_name, where)

    try:
      return _wmi_watcher (
        self._namespace.ExecNotificationQuery (wql),
        is_extrinsic=is_extrinsic,
        fields=fields
      )
    except pywintypes.com_error:
      handle_com_error ()

  def __getattr__ (self, attribute):
    """Offer WMI classes as simple attributes. Pass through any untrapped
    unattribute to the underlying OLE object. This means that new or
    unmapped functionality is still available to the module user.
    """
    #
    # Don't try to match against known classes as was previously
    # done since the list may not have been requested
    # (find_classes=False).
    #
    try:
      return self._cached_classes (attribute)
    except pywintypes.com_error:
      return getattr (self._namespace, attribute)

  def _cached_classes (self, class_name):
    """Standard caching helper which keeps track of classes
    already retrieved by name and returns the existing object
    if found. If this is the first retrieval, store it and
    pass it back
    """
    if class_name not in self._classes_map:
      self._classes_map[class_name] = _wmi_class (self, self._namespace.Get (class_name))
    return self._classes_map[class_name]

  def _getAttributeNames (self):
    """Return list of classes for IPython completion engine"""
    return [x for x in self.classes if not x.startswith ('__')]

#
# class _wmi_watcher
#
class _wmi_watcher:
  """Helper class for WMI.watch_for below (qv)"""

  _event_property_map = {
    "TargetInstance" : _wmi_object,
    "PreviousInstance" : _wmi_object
  }
  def __init__ (self, wmi_event, is_extrinsic, fields=[]):
    self.wmi_event = wmi_event
    self.is_extrinsic = is_extrinsic
    self.fields = fields

  def __call__ (self, timeout_ms=-1):
    """When called, return the instance which caused the event. Supports
     timeout in milliseconds (defaulting to infinite). If the watcher
     times out, :exc:`x_wmi_timed_out` is raised. This makes it easy to support
     watching for multiple objects.
    """
    try:
      event = self.wmi_event.NextEvent (timeout_ms)
      if self.is_extrinsic:
        return _wmi_event (event, None, self.fields)
      else:
        return _wmi_event (
          event.Properties_ ("TargetInstance").Value,
          _wmi_object (event, property_map=self._event_property_map),
          self.fields
        )
    except pywintypes.com_error:
      handle_com_error ()

PROTOCOL = "winmgmts:"
def connect (
  computer="",
  impersonation_level="",
  authentication_level="",
  authority="",
  privileges="",
  moniker="",
  wmi=None,
  namespace="",
  suffix="",
  user="",
  password="",
  find_classes=False,
  debug=False
):
  """The WMI constructor can either take a ready-made moniker or as many
  parts of one as are necessary. Eg::

    c = wmi.WMI (moniker="winmgmts:{impersonationLevel=Delegate}//remote")
    # or
    c = wmi.WMI (computer="remote", privileges=["!RemoteShutdown", "Security"])

  I daren't link to a Microsoft URL; they change so often. Try Googling for
  WMI construct moniker and see what it comes back with.

  For complete control, a named argument "wmi" can be supplied, which
  should be a SWbemServices object, which you create yourself. Eg::

    loc = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    svc = loc.ConnectServer(...)
    c = wmi.WMI(wmi=svc)

  This is the only way of connecting to a remote computer with a different
  username, as the moniker syntax does not allow specification of a user
  name.

  If the `wmi` parameter is supplied, all other parameters are ignored.
  """
  global _DEBUG
  _DEBUG = debug

  try:
    try:
      if wmi:
        obj = wmi

      elif moniker:
        if not moniker.startswith (PROTOCOL):
          moniker = PROTOCOL + moniker
        obj = GetObject (moniker)

      else:
        if user:
          if privileges or suffix:
            raise x_wmi_authentication ("You can't specify privileges or a suffix as well as a username")
          elif computer in (None, '', '.'):
            raise x_wmi_authentication ("You can only specify user/password for a remote connection")
          else:
            obj = connect_server (
              server=computer,
              namespace=namespace,
              user=user,
              password=password,
              authority=authority,
              impersonation_level=impersonation_level,
              authentication_level=authentication_level
            )

        else:
          moniker = construct_moniker (
            computer=computer,
            impersonation_level=impersonation_level,
            authentication_level=authentication_level,
            authority=authority,
            privileges=privileges,
            namespace=namespace,
            suffix=suffix
          )
          obj = GetObject (moniker)

      wmi_type = get_wmi_type (obj)

      if wmi_type == "namespace":
        return _wmi_namespace (obj, find_classes)
      elif wmi_type == "class":
        return _wmi_class (None, obj)
      elif wmi_type == "instance":
        return _wmi_object (obj)
      else:
        raise x_wmi ("Unknown moniker type")

    except pywintypes.com_error:
      handle_com_error ()

  except x_wmi_uninitialised_thread:
    raise x_wmi_uninitialised_thread ("WMI returned a syntax error: you're probably running inside a thread without first calling pythoncom.CoInitialize[Ex]")

WMI = connect

def construct_moniker (
  computer=None,
  impersonation_level=None,
  authentication_level=None,
  authority=None,
  privileges=None,
  namespace=None,
  suffix=None
):
  security = []
  if impersonation_level: security.append ("impersonationLevel=%s" % impersonation_level)
  if authentication_level: security.append ("authenticationLevel=%s" % authentication_level)
  #
  # Use of the authority descriptor is invalid on the local machine
  #
  if authority and computer: security.append ("authority=%s" % authority)
  if privileges: security.append ("(%s)" % ", ".join (privileges))

  moniker = [PROTOCOL]
  if security: moniker.append ("{%s}!" % ",".join (security))
  if computer: moniker.append ("//%s/" % computer)
  if namespace:
    parts = re.split (r"[/\\]", namespace)
    if parts[0] != 'root':
      parts.insert (0, "root")
    moniker.append ("/".join (parts))
  if suffix: moniker.append (":%s" % suffix)
  return "".join (moniker)

def get_wmi_type (obj):
  try:
    path = obj.Path_
  except AttributeError:
    return "namespace"
  else:
    if path.IsClass:
      return "class"
    else:
      return "instance"

def connect_server (
  server,
  namespace = "",
  user = "",
  password = "",
  locale = "",
  authority = "",
  impersonation_level="",
  authentication_level="",
  security_flags = 0x80,
  named_value_set = None
):
  """Return a remote server running WMI

  :param server: name of the server
  :param namespace: namespace to connect to - defaults to whatever's defined as default
  :param user: username to connect as, either local or domain (dom\\name or user@domain for XP)
  :param password: leave blank to use current context
  :param locale: desired locale in form MS_XXXX (eg MS_409 for Am En)
  :param authority: either "Kerberos:" or an NT domain. Not needed if included in user
  :param impersonation_level: valid WMI impersonation level
  :param security_flags: if 0, connect will wait forever; if 0x80, connect will timeout at 2 mins
  :param named_value_set: typically empty, otherwise a context-specific `SWbemNamedValueSet`

  Example::

    remote_connetion = wmi.connect_server (
      server="remote_machine", user="myname", password="mypassword"
    )
    c = wmi.WMI (wmi=remote_connection)
  """
  #
  # Thanks to Matt Mercer for example code to set
  # impersonation & authentication on ConnectServer
  #
  if impersonation_level:
    try:
      impersonation = getattr (obj._constants, "wbemImpersonationLevel%s" % impersonation_level.title ())
    except AttributeError:
      raise x_wmi_authentication ("No such impersonation level: %s" % impersonation_level)
  else:
    impersonation = None

  if authentication_level:
    try:
      authentication = getattr (obj._constants, "wbemAuthenticationLevel%s" % authentication_level.title ())
    except AttributeError:
      raise x_wmi_authentication ("No such impersonation level: %s" % impersonation_level)
  else:
    authentication = None

  server = Dispatch ("WbemScripting.SWbemLocator").\
    ConnectServer (
      server,
      namespace,
      user,
      password,
      locale,
      authority,
      security_flags,
      named_value_set
    )
  if impersonation:
    server.Security_.ImpersonationLevel  = impersonation
  if authentication:
    server.Security_.AuthenticationLevel  = authentication
  return server

def Registry (
  computer=None,
  impersonation_level="Impersonate",
  authentication_level="Default",
  authority=None,
  privileges=None,
  moniker=None
):

  warnings.warn ("This function can be implemented using wmi.WMI (namespace='DEFAULT').StdRegProv", DeprecationWarning)
  if not moniker:
    moniker = construct_moniker (
      computer=computer,
      impersonation_level=impersonation_level,
      authentication_level=authentication_level,
      authority=authority,
      privileges=privileges,
      namespace="default",
      suffix="StdRegProv"
    )

  try:
    return _wmi_object (GetObject (moniker))

  except pywintypes.com_error:
    handle_com_error ()

#
# Typical use test
#
if __name__ == '__main__':
  system = WMI ()
  for my_computer in system.Win32_ComputerSystem ():
    print ("Disks on", my_computer.Name)
    for disk in system.Win32_LogicalDisk ():
      print (disk.Caption, disk.Description, disk.ProviderName or "")

