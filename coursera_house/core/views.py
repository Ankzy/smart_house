from django.urls import reverse_lazy
from django.views.generic import FormView
from django.http import HttpResponse
from .form import ControllerForm
from .tasks import CleverSystem, DBSettings


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')
    states = None

    def get(self, request, *args, **kwargs):
        self.states = CleverSystem.get_controller_state()
        if CleverSystem.resp_get_code != 200:
            return HttpResponse(status=502)
        return super().get(request, *args, **kwargs)

#### 1!
    def post(self, request, *args, **kwargs):
        self.states = CleverSystem.get_controller_state()
        print(CleverSystem.resp_get_code)
        if CleverSystem.resp_get_code != 200:
            return HttpResponse(status=502)
        return super().post(request, *args, **kwargs)

#### ! 3
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['data'] = self.states
        return context

    def get_initial(self):
        # This method set default form values.
        bedroom_target_temperature = DBSettings.get_value('bedroom_target_temperature')
        hot_water_target_temperature = DBSettings.get_value('hot_water_target_temperature')
        return {'bedroom_target_temperature': bedroom_target_temperature,
                'hot_water_target_temperature': hot_water_target_temperature,
                'bedroom_light': self.states['bedroom_light'],
                'bathroom_light': self.states['bathroom_light']}

##### ! 2
    def form_valid(self, form):
        # This method is called when valid form data was posted.
        bedroom_temperature = form.cleaned_data['bedroom_target_temperature']
        water_temperature = form.cleaned_data['hot_water_target_temperature']
        DBSettings.set_value('bedroom_target_temperature', bedroom_temperature)
        DBSettings.set_value('hot_water_target_temperature', water_temperature)
        bedroom_light = form.cleaned_data['bedroom_light']
        bathroom_light = form.cleaned_data['bathroom_light']
        new_states = {}
        if self.states['bedroom_light'] != bedroom_light:
            new_states['bedroom_light'] = bedroom_light
        if self.states['bathroom_light'] != bathroom_light:
            new_states['bathroom_light'] = bathroom_light
        if new_states:
            CleverSystem.put_controller_state(new_states)
        return super(ControllerView, self).form_valid(form)
