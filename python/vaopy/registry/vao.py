"""
a module for basic VO Registry interactions.  

A VO registry is a database of VO resources--data collections and
services--that are available for VO applications.  Typically, it is 
aware of the resources from all over the world.  A registry can find 
relevent data collections and services through search
queries--typically, subject-based.  The registry responds with a list
of records describing matching resources.  With a record in hand, the 
application can use the information in the record to access the 
resource directly.  Most often, the resource is a data service that
can be queried for individual datasets of interest.  

This module provides basic, low-level access to the VAO Registry at 
STScI using (proprietary) VOTable-based services.  In most cases,
the Registry task, with its higher-level features (e.g. result caching
and resource aliases), can be a more convenient interface.  The more  
basic interface provided here allows developers to code their own 
interaction models.  
"""

from ..dal import query as dalq
from urllib import quote_plus, urlopen, urlretrieve

def regsearch(keywords=None, servicetype=None, 
              waveband=None, sqlpred=None):
    """
    execute a simple query to the VAO registry.  

    :Args:
      *keywords*:  a string giving a single term or a python list 
                     of terms to match to registry records.  
      *servicetype:  the service type to restrict results to; 
                     allowed values include 'catalog' (synonyms: 
                     'scs', 'conesearch'), 'image' (synonym: 'sia'), 
                     'spectrum' (synonym: 'ssa'). 'service' (a generic
                     service). 'table' (synonyms: 'tap', 'database').
      *waveband*:  the name of a desired waveband; resources returned 
                     will be restricted to those that indicate as having
                     data in that waveband.
      *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                     that further contrains the search against supported 
                     keywords.

    The result will be a RegistryResults instance.  
    """
    reg = RegistryService()
    return reg.search(keywords, servicetype, waveband, sqlpred)


class RegistryService(dalq.DalService):
    """
    a class for submitting searches to the VAO registry.  
    """

    STSCI_REGISTRY_BASEURL = "http://vao.stsci.edu/directory/NVORegInt.asmx/"

    def __init__(self, baseurl=None, resmeta=None):
        """
        connect to an STScI registry at the given URL
        :Args:
           *baseurl*:  the base URL for submitting search queries to the 
                         service.  If None, it will default to the STScI 
                         public registry
           *resmeta*:  an optional dictionary of properties about the 
                         service
        """
        if not baseurl:  baseurl = self.STSCI_REGISTRY_BASEURL
        if not baseurl.endswith("/"): baseurl += "/"

        dalq.DalService.__init__(self, baseurl, resmeta)


    def search(self, keywords=None, servicetype=None, 
               waveband=None, sqlpred=None):
        """
        execute a simple registry search of the specified
        keywords. 

        :Args:
          *keywords*:  a string giving a single term or a python list 
                         of terms to match to registry records.  
          *servicetype:  the service type to restrict results to; 
                         allowed values include 'catalog' (synonyms: 
                         'scs', 'conesearch'), 'image' (synonym: 'sia'), 
                         'spectrum' (synonym: 'ssa'). 'service' (a generic
                         service). 'table' (synonyms: 'tap', 'database').
          *waveband*:  the name of a desired waveband; resources returned 
                         will be restricted to those that indicate as having
                         data in that waveband.
          *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                         that further contrains the search against supported 
                         keywords.

        The result will be a RegistryResults instance.  
        """
        srch = self.createQuery(keywords, servicetype, waveband, sqlpred)
        return srch.execute()
        
    
    def resolve(self, ivoid):
        """
        Resolve the identifier against the registry, returning a
        resource record.  
        @param ivoid          the IVOA Identifier of the resource
        """
        srch = self.createQuery()
        srch.addPredicate("Identifier='%s'" % ivoid)
        res = srch.execute()
        return res.getRecord(0)

    def createQuery(self, keywords=None, servicetype=None, 
                    waveband=None, sqlpred=None):
        """
        create a RegistryQuery object that can be refined or saved
        before submitting.  
        :Args:
          *keywords*:  a string giving a single term or a python list 
                         of terms to match to registry records.  
          *servicetype:  the service type to restrict results to; 
                         allowed values include 'catalog' (synonyms: 
                         'table', 'scs', 'conesearch', 'ConeSearch'), 
                         'image' (synonym: 'sia', 'SimpleImageAccess'), 
                         'spectrum' (synonym: 'ssa', 'ssap', 
                         'SimpleSpectralAccess'). 
                         'database' (synonyms: 'tap','TableAccess').
          *waveband*:  the name of a desired waveband; resources returned 
                         will be restricted to those that indicate as having
                         data in that waveband.
          *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                         that further contrains the search against supported 
                         keywords.
        """
        srch = RegistryQuery(self._baseurl)
        if sqlpred:
            srch.addpredicate(sqlpred)
        if waveband:
            srch.waveband = waveband
        if servicetype:
            srch.servicetype = servicetype
        if keywords:
            srch.addkeywords(keywords)
        return srch

class RegistryQuery(dalq.DalQuery):
    """
    a representation of a registry query that can be built up over
    successive method calls and then executed.  An instance is normally
    obtained via a call to RegistrySearch.createQuery()
    """
    
    SERVICE_NAME = "VOTCapBandPredOpt"
    RESULTSET_TYPE_ARG = "VOTStyleOption=2"
    ALLOWED_WAVEBANDS = "Radio Millimeter Infrared Optical UV".split() + \
        "EUV X-ray Gamma-ray".split()
    WAVEBAND_SYN = { "ir":  "Infrared",
                     "IR":  "Infrared",
                     "uv":  "UV",
                     "euv": "EUV" }
                     
    ALLOWED_CAPS = { "table": "ConeSearch", 
                     "catalog": "ConeSearch", 
                     "scs": "ConeSearch", 
                     "conesearch": "ConeSearch", 
                     "image": "SimpleImageAccess",
                     "sia": "SimpleImageAccess",
                     "spectra": "SimpleSpectralAccess",
                     "spectrum": "SimpleSpectralAccess",
                     "ssa": "SimpleSpectralAccess",
                     "ssap": "SimpleSpectralAccess",
                     "line": "SimpleLineAccess",
                     "sla": "SimpleLineAccess",
                     "slap": "SimpleLineAccess",
                     "tap": "TableAccess",
                     "database": "TableAccess",
                     "tableAccess": "TableAccess",
                     "simpleImageAccess": "SimpleImageAccess",
                     "simpleLineAccess": "SimpleLineAccess",
                     "simpleSpectralAccess": "SimpleSpectralAccess"  }
                     

    def __init__(self, orKeywords=True, baseurl=None):
        """
        create the query instance

        :Args:
           *orKeywords*:  if True, keyword constraints will by default be 
                            OR-ed together; that is, a resource that matches 
                            any of the keywords will be returned.  If FALSE,
                            the keywords will be AND-ed, thus requiring a 
                            resource to match all the keywords.  
           *baseurl*:     the base URL for the VAO registry.  If None, it will
                            be set to the public VAO registry at STScI.  
        """
        if not baseurl:  baseurl = RegistryService.STSCI_REGISTRY_BASEURL
        dalq.DalQuery.__init__(self, baseurl)
        self._kw = []          # list of individual keyword phrases
        self._preds = []       # list of SQL predicates
        self._svctype = None
        self._orKw = orKeywords
        self._doSort = True
        self._dalonly = False

    @property
    def keywords(self):
        """
        return the current set of keyword constraints

        To update, use addkeywords(), removekeywords(), or clearkeywords().
        """
        return list(self._kw)

    def addkeywords(self, keywords):
        """
        add keywords that should be added to this query.  Keywords 
        are searched against key fields in the registry record.  A
        keyword can in fact be a phrase--a sequence of words; in this
        case the sequence of words must appear verbatim in the record
        for that record to be matched. 
        @param keywords  either a single keyword phrase (as a string) 
                           or a list of keyword phrases to add to the 
                           query.  
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        self._kw.extend(keywords)

    def removekeywords(self, keywords):
        """
        remove the given keyword or keywords from the query.  A
        keyword can in fact be a phrase--a sequence of words; in this
        case, the phrase will be remove.  
        @param keywords  either a single keyword phrase (as a string) 
                           or a list of keyword phrases to remove from
                           the query.  
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        for kw in keywords:
            self._kw.remove(kw)

    def clearkeywords(self):
        """
        remove all keywords that have been added to this query.
        """
        self._kw = []

    def or_keywords(self, ored):
        """
        set whether keywords are OR-ed or AND-ed together.  When
        the keywords are OR-ed, returned records will match at 
        least one of the keywords.  When they are AND-ed, the 
        records will match all of the keywords provided.  
        @param ored   true, if the keywords should be OR-ed; false,
                        if they should be AND-ed.
        """
        self._orKw = ored

    def will_or_keywords(self):
        """
        set true if the keywords will be OR-ed or AND-ed together
        in the query.  True is returned if the keywords will be 
        OR-ed.  
        """
        return self._orKw

    @property
    def servicetype(self):
        """
        the type of service that query results will be restricted to.
        """
        return self._svctype
    @servicetype.setter
    def servicetype(self, val):
        if not val:
            raise ValueError("missing serviceType value");
        if len(val) < 2:
            raise ValueError("unrecognized serviceType value: " + 
                             serviceType);

        # uncapitalize
        if val[0].upper() == val[0]:
            val = val[0].lower() + val[1:]

        if val not in self.ALLOWED_CAPS.keys():
            raise ValueError("unrecognized servicetype value: " + val);
                             
        self._svctype = val
    @servicetype.deleter
    def servicetype(self):
        self._svctype = None

    @property
    def waveband(self):
        """
        the waveband to restrict the query by.  The query results will 
        include only those resourse that indicate they have data from this 
        waveband.  Allowed values include:
        """
        return self.getparam("waveband")
    @waveband.setter
    def waveband(self, band):
        if band is None:
            self.unsetparam("waveband")
            return

        if not isinstance(band, str):
            raise ValueError("band should be a string; got: " + str(type(band)))
        if not band:
            raise ValueError("missing waveband value");
        if len(band) < 2:
            raise ValueError("unrecognized waveband: " + band);

        _band = band
        if self.WAVEBAND_SYN.has_key(band):
            _band = self.WAVEBAND_SYN[band]

        # capitalize
        _band = _band[0].upper() + _band[1:]
        if _band not in self.ALLOWED_WAVEBANDS:
            raise ValueError("unrecognized waveband: " + band)
        self.setparam("waveband", _band)
    @waveband.deleter
    def waveband(self):
        self.unsetparam("waveband")

    @property
    def predicates(self):
        """
        the (read-only) list of predicate constraints that will 
        be applied to the query.  These will be AND-ed with all other 
        constraints (including previously added predicates); that is, 
        this constraint must be satisfied in addition to the other 
        constraints to match a particular resource record.  

        To update, use addpredicate(), removepredicate(), or clearpredicate().
        """
        return list(self._preds)

    def addpredicate(self, pred):
        """
        add an SQL search predicate to the query.  This predicate should
        be of form supported by STScI VOTable search services.  This 
        predicate will be AND-ed with all other constraints (including
        previously added predicates); that is, this constraint must be
        satisfied in addition to the other constraints to match a 
        particular resource record.
        """
        self._preds.append(pred)

    def removepredicate(self, pred):
        """
        remove the give predicate from the current set of predicate
        constraints.  
        """
        self._preds.remove(pred)

    def clearpredicates(self):
        """
        remove all previously added predicates.
        """
        self._preds = []

    def execute(self):
        """
        submit the query and return the results as a RegistryResults
        instance.  
        @throws RegistryServiceError   for errors connecting to or 
                    communicating with the service
        @throws RegistryQueryError     if the service responds with 
                    an error, including a query syntax error.  A 
                    syntax error should only occur if the query 
                    query contains non-sensical predicates.
        """
        return RegistryResults(self.executeVotable(), self.getQueryURL())

    def getQueryURL(self, lax=False):
        """
        return the GET URL that will submit the query and return the 
        results as a VOTable
        """
        url = "%s%s?%s" % (self._baseurl, self.SERVICE_NAME, 
                           self.RESULTSET_TYPE_ARG)

        # this will add waveband 
        if len(self.paramnames()) > 0:
            url += "&" + \
             "&".join(map(lambda p: "%s=%s"%(p,self._paramtostr(self._param[p])),
                          self._param.keys()))

        if (self.servicetype):
            url += "&capability=%s" % self._toCapConst(self.servicetype)
        else:
            url += "&capability="

        preds = list(self._preds)
        if (self.keywords): 
            preds.append(self.keywords_to_predicate(self.keywords, self._orKw))
        if (preds):
            url += "&predicate=%s" % \
                quote_plus(" AND ".join(map(lambda p: "(%s)" % p, preds)))
                              
        else:
            url += "&predicate=1"

        return url
        
    def _toCapConst(self, stype):
        return self.ALLOWED_CAPS[stype]

    def keywords_to_predicate(self, keywords, ored=True):
        """
        return the given keywords as a predicate that can be added to
        the current query.  This function can be overridden to change
        how keyword searches are implemented.  

        :Args:
          *keywords*  a python list of the keywords
          *ored*      if True, the keywords should be ORed together; 
                          otherwise, they should be ANDed
        """
        textcols = ["Title", "ShortName", "Identifier", 
                    "[content/subject]", "[curation/publisher]", 
                    "[content/description]", "[@xsi_type]", 
                    "[capability/@xsi_type]"]

        conjunction = (ored and ") OR (") or ") AND ("

        const = []
        for kw in keywords:
            keyconst = []
            for col in textcols:
                keyconst.append("%s LIKE '%%%s%%'" % (col, kw))
            const.append(" OR ".join(keyconst))
        return "("+conjunction.join(const)+")"

class RegistryResults(dalq.DalResults):
    """
    an iterable set of results from a registry query.  Each record is
    returned as SimpleResource instance
    """

    _strarraycols = ["waveband", "subject", "type", "contentLevel"]

    def __init__(self, votable, url=None):
        """
        initialize the results.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SIAQuery's execute().
        """
        dalq.DalResults.__init__(self, votable, url)

    def getrecord(self, index):
        """
        return all the attributes of a resource record with the given index
        as SimpleResource instance (a dictionary-like object).
        @param index  the zero-based index of the record
        """
        return SimpleResource(self, index)

    def getvalue(self, name, index):
        """
        return the value of a record attribute--a value from a column and row.

        This implementation is aware of how lists of strings are encoded 
        and will return a python list of strings accordingly.

        :Args:
           *name*:   the name of the attribute (column)
           *index*:  the zero-based index of the record

        :Raises:
           IndexError  if index is negative or equal or larger than the 
                         number of rows in the result table.
           KeyError    if name is not a recognized column name
        """
        out = dalq.DalResults.getvalue(self, name, index)
        if name not in self._strarraycols:
            return out

        if out[0] == '#': out = out[1:]
        if out[-1] == '#': out = out[:-1]
        return tuple(out.split('#'))


class SimpleResource(dalq.Record):
    """
    a dictionary for the resource attributes returned by a registry query.
    A SimpleResource is a dictionary, so in general, all attributes can 
    be accessed by name via the [] operator, and the attribute names can 
    by returned via the keys() function.  For convenience, it also stores 
    key values as public python attributes; these include:

       title         the title of the resource
       shortname     the resource's short name
       ivoid         the IVOA identifier for the resource
       accessurl     when the resource is a service, the service's access 
                       URL.
    """

    def __init__(self, results, index):
        dalq.Record.__init__(self, results, index)

    @property
    def title(self):
        """
        """
        return self.get("title")

    @property
    def shortname(self):
        """
        """
        return self.get("shortName")

    @property
    def tags(self):
        """
        """
        return self.get("tags")

    @property
    def ivoid(self):
        """
        """
        return self.get("identifier")

    @property
    def publisher(self):
        """
        """
        return self.get("publisher")

    @property
    def waveband(self):
        """
        """
        return self.get("waveband")

    @property
    def subject(self):
        """
        """
        return self.get("subject")

    @property
    def type(self):
        """
        """
        return self.get("type")

    @property
    def contentlevel(self):
        """
        """
        return self.get("contentLevel")

    @property
    def capability(self):
        """
        """
        return self.get("capabilityClass")

    @property
    def standardid(self):
        """
        """
        return self.get("capabilityStandardID")

    @property 
    def accessurl(self):
        """
        """
        return self.get("accessURL")
