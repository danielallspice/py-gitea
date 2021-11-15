from .exceptions import ObjectIsInvalid, MissiongEqualyImplementation,RawRequestEndpointMissing



class ReadonlyApiObject:

    def __init__(self, gitea):
        self.gitea = gitea
        self.deleted = False  # set if .delete was called, so that an exception is risen

    def __str__(self):
        return "GiteaAPIObject (%s):" % (type(self))

    def __eq__(self, other):
        """Compare only fields that are part of the gitea-data identity"""
        raise MissiongEqualyImplementation()

    def __hash__(self):
        """Hash only fields that are part of the gitea-data identity"""
        raise MissiongEqualyImplementation()

    fields_to_parsers = {}

    @classmethod
    def request(cls, gitea, id):
        if hasattr("GET_API_OBJECT", cls):
            return cls._request(gitea)
        else:
            raise RawRequestEndpointMissing()

    @classmethod
    def _request(cls, gitea, args):
        result = cls._get_gitea_api_object(gitea, args)
        api_object = cls.parse_response(gitea, result)
        # hack: not all necessary request args in api result (e.g. repo name in issue)
        for key, value in args.items():
            if not hasattr(api_object, key):
                setattr(api_object, key, value)
        return api_object

    @classmethod
    def _get_gitea_api_object(cls, gitea, args):
        """Retrieving an object always as GET_API_OBJECT """
        return gitea.requests_get(cls.GET_API_OBJECT.format(**args))

    @classmethod
    def parse_response(cls, gitea, result) -> "ReadonlyApiObject":
        # gitea.logger.debug("Found api object of type %s (id: %s)" % (type(cls), id))
        api_object = cls(gitea)
        cls._initialize(gitea, api_object, result)
        return api_object

    @classmethod
    def _initialize(cls, gitea, api_object, result):
        for name, value in result.items():
            if name in cls.fields_to_parsers and value is not None:
                parse_func = cls.fields_to_parsers[name]
                value = parse_func(gitea, value)
            cls._add_read_property(name, value, api_object)
        # add all patchable fields missing in the request to be writable
        for name in cls.fields_to_parsers.keys():
            if not hasattr(api_object,name):
                cls._add_read_property(name, None, api_object)

    @classmethod
    def _add_read_property(cls, name, value, api_object):
        if not hasattr(api_object, name):
            prop = property(
                (lambda name: lambda self: self._get_var(name))(name))
            setattr(cls, name, prop)
            setattr(api_object, "_" + name, value)
        else:
            raise AttributeError(f"Attribute {name} already exists on api object.")

    def _get_var(self, name):
        if self.deleted:
            raise ObjectIsInvalid()
        return getattr(self, "_" + name)


class ApiObject(ReadonlyApiObject):

    patchable_fields = set()

    def __init__(self, gitea):
        super().__init__(gitea)
        self.dirty_fields = set()

    def commit(self):
        raise NotImplemented()

    def get_dirty_fields(self):
        return {name: getattr(self, name) for name in self.dirty_fields}

    @classmethod
    def _initialize(cls, gitea, api_object, result):
        super()._initialize(gitea,api_object,result)
        for name, value in result.items():
            if name in cls.patchable_fields:
                cls._add_write_property(name,value,api_object)
        # add all patchable fields missing in the request to be writable
        for name in cls.patchable_fields:
            if not hasattr(api_object,name):
                cls._add_write_property(name, None, api_object)

    @classmethod
    def _add_write_property(cls, name, value, api_object):
        prop = property(
            (lambda name: lambda self: self._get_var(name))(name),
            (lambda name: lambda self, v: self.__set_var(name, v))(name))
        setattr(cls, name, prop)
        setattr(api_object, "_" + name, value)

    def __set_var(self, name, i):
        if self.deleted:
            raise ObjectIsInvalid()
        self.dirty_fields.add(name)
        setattr(self, "_" + name, i)