from django.db.models.query import Prefetch


PK_FIELD_NAME = 'pk'


class ModelQueryGraph:
    def __init__(
            self, ModelClass,
            *non_many_related_field_names,
            ORDER=True,
            **fk_and_many_related_field_names_and_corresponding_model_query_graphs):
        if PK_FIELD_NAME in non_many_related_field_names:
            assert not ORDER

        self.ModelClass = ModelClass
        
        all_non_many_related_field_names = \
            {field.name
             for field in ModelClass._meta.fields}

        all_non_many_related_field_names.add(PK_FIELD_NAME)

        assert all_non_many_related_field_names.issuperset(non_many_related_field_names)

        _overlapping_field_names = \
            set(non_many_related_field_names).intersection(
                fk_and_many_related_field_names_and_corresponding_model_query_graphs)

        assert not _overlapping_field_names, \
            '*** {} ***'.format(_overlapping_field_names)

        fk_model_query_graphs = {}
        self.many_related_model_query_graphs = {}

        for fk_or_many_related_field_name, fk_or_many_related_model_query_graph \
                in fk_and_many_related_field_names_and_corresponding_model_query_graphs.items():
            assert isinstance(fk_or_many_related_model_query_graph, ModelQueryGraph)

            if fk_or_many_related_field_name in all_non_many_related_field_names:
                fk_model_query_graphs[fk_or_many_related_field_name] = \
                    fk_or_many_related_model_query_graph

            else:
                self.many_related_model_query_graphs[fk_or_many_related_field_name] = \
                    fk_or_many_related_model_query_graph

        self.select_related = tuple(fk_model_query_graphs)
        self.field_names = non_many_related_field_names

        for fk_field_name, fk_model_query_graph in fk_model_query_graphs.items():
            self.select_related += \
                tuple('{}__{}'.format(fk_field_name, fk_model_select_related)
                      for fk_model_select_related in fk_model_query_graph.select_related)

            self.field_names += \
                tuple('{}__{}'.format(fk_field_name, fk_model_field_name)
                      for fk_model_field_name in fk_model_query_graph.field_names)

            for fk_many_related_field_name, fk_many_related_model_query_graph \
                    in fk_model_query_graph.many_related_model_query_graphs.items():
                self.many_related_model_query_graphs['{}__{}'.format(fk_field_name, fk_many_related_field_name)] = \
                    fk_many_related_model_query_graph

        if ORDER:
            if ORDER is True:
                self.order = True

            else:
                if isinstance(ORDER, str):
                    self.order = ORDER,

                else:
                    assert isinstance(ORDER, (list, tuple))

                    self.order = ORDER

        else:
            self.order = None

    def __repr__(self):
        return '{}{}\nONLY({}){}{}'.format(

                self.ModelClass.__name__,

                '\nSELECT_RELATED({})'.format(
                    ', '.join(self.select_related))
                    if self.select_related
                    else '',

                ', '.join(self.field_names),

                '\nORDER_BY({})'.format(
                    ', '.join(self.order))
                    if isinstance(self.order, (list, tuple))
                    else '',

                '\nPREFETCH_RELATED(\n{}\n)'.format(
                    '\n\n'.join(
                        '{}: {}'.format(
                            many_related_field_name,
                            many_related_model_query_graph)
                        for many_related_field_name, many_related_model_query_graph
                            in self.many_related_model_query_graphs.items()))
                    if self.many_related_model_query_graphs
                    else '')

    def __str__(self):
        return repr(self)

    def query_set(self, init=None):
        qs = self.ModelClass.objects \
            if init is None \
            else init

        if self.select_related:
            qs = qs.select_related(*self.select_related)

        qs = qs.only(*self.field_names)

        if self.order:
            if isinstance(self.order, (list, tuple)):
                qs = qs.order_by(*self.order)
                
            else:
                assert self.order is True

        else:
            qs = qs.order_by()

        if self.many_related_model_query_graphs:
            qs = qs.prefetch_related(
                    *(Prefetch(
                        lookup=many_related_field_name,
                        queryset=many_related_model_query_graph.query_set())
                      for many_related_field_name, many_related_model_query_graph
                        in self.many_related_model_query_graphs.items()))

        return qs
