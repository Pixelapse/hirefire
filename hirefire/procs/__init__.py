from ..utils import import_attribute, OrderedDict


__all__ = ('loaded_procs', 'Proc', 'load_proc', 'load_procs')


class Procs(OrderedDict):
    pass

loaded_procs = Procs()


def load_proc(obj):
    if isinstance(obj, Proc):
        return obj
    elif isinstance(obj, basestring):
        try:
            proc = import_attribute(obj)
        except ImportError as e:
            raise ValueError('The proc %r could not be imported: %s' %
                             (obj, e))
        except AttributeError as e:
            raise ValueError('The proc %r could not be found: %s' %
                             (obj, e))
        if not isinstance(proc, Proc):
            proc = proc()
        return proc
    raise ValueError('The proc %r could not be loaded' % obj)


def load_procs(*procs):
    """
    Given a list of dotted import paths or Proc subclasses
    populates the procs list.

    Example::

        load('mysite.procs.WorkerCeleryProc', 'mysite.proc.ThumbnailsRQProc')
        load(worker_rq_proc)
        load('mysite.proc.worker_rq_proc')

    """
    for obj in procs:
        proc = load_proc(obj)
        if proc.name in loaded_procs:
            raise ValueError('Given proc %r overlaps with '
                             'another already loaded proc (%r)' %
                             (proc, loaded_procs[proc.name]))
        loaded_procs[proc.name] = proc
    return loaded_procs


class Proc(object):
    """
    The base proc class. Use this to implement custom queues or
    other behaviours, e.g.::

        import mysite.sekrit
        from hirefire import procs

        class MyCustomProc(procs.Proc):
            name = 'worker'
            queues = ['default']

            def quantity(self):
                return sum([mysite.sekrit.count(queue)
                            for queue in self.queues])

    :param name: the name of the proc (required)
    :param queues: list of queue names to check (required)
    :type name: str
    :type queues: str or list of str

    """
    #: The name of the proc
    name = None

    #: The list of queues to check
    queues = []

    def __init__(self, name=None, queues=None):
        if name is not None:
            self.name = name
        if self.name is None:
            raise ValueError('The proc %r requires a name '
                             'attribute' % self)
        if queues is not None:
            self.queues = queues
        if not isinstance(self.queues, (list, tuple)):
            self.queues = (queues,)
        if not self.queues:
            raise ValueError('The proc %r requires at least '
                             'one queue to check' % self)

    def __unicode__(self):
        return self.name or 'unnamed'

    def __repr__(self):
        cls = self.__class__
        return ("<Proc %s: '%s.%s'>" %
                (self.name, cls.__module__, cls.__name__))

    def quantity(self, *args, **kwargs):
        """
        Returns the aggregated number of tasks of the proc queues.

        Needs to be implemented in a subclass.
        """
        raise NotImplementedError


class ClientProc(Proc):
    """
    A special subclass of the :class:`~hirefire.procs.Proc` class
    that instantiates a list of clients for each given queue, e.g.::

        import mysite.sekrit
        from hirefire import procs

        class MyCustomProc(procs.ClientProc):
            name = 'worker'
            queues = ['default']

            def client(self, queue):
                return mysite.sekrit.Client(queue)

            def quantity(self):
                return sum([client.count(queue)
                            for client in self.clients])

    See the implementation of the :class:`~hirefire.procs.rq.RQProc`
    class for an example.

    """
    def __init__(self, *args, **kwargs):
        super(ClientProc, self).__init__(*args, **kwargs)
        self.clients = []
        for queue in self.queues:
            client = self.client(queue)
            if client is None:
                continue
            self.clients.append(client)

    def client(self, queue, *args, **kwargs):
        """
        Returns a client instance for the given queue to be used
        in the ``quantity`` method.

        Needs to be implemented in a subclass.
        """
        raise NotImplementedError
