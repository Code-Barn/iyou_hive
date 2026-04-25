from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import TimelineEvent
import markdown


@login_required
def timeline_view(request):
    events = TimelineEvent.objects.all()
    return render(request, 'timeline/timeline.html', {'events': events})



@login_required
def home(request):
    return timeline_view(request)


@login_required
def upload_markdown(request):
    if request.method == 'POST':
        content = request.POST.get('markdown_content', '')
        events = parse_markdown(content)
        for event_data in events:
            TimelineEvent.objects.create(**event_data)
        return HttpResponse("Timeline uploaded successfully")
    return render(request, 'timeline/upload.html')


@login_required
def event_detail(request, pk):
    event = get_object_or_404(TimelineEvent, pk=pk)
    return render(request, 'timeline/event_detail.html', {'event': event})


def parse_markdown(content):
    events = []
    lines = content.split('\n')
    current_event = {}

    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            if current_event:
                events.append(current_event)
            try:
                current_event = {'date': line[2:], 'event': '', 'category': '', 'supporting_docs': None, 'notes': ''}
            except ValueError:
                continue
        elif line.startswith('**Event:**'):
            current_event['event'] = line[10:].strip()
        elif line.startswith('**Category:**'):
            current_event['category'] = line[13:].strip()
        elif line.startswith('**Notes:**'):
            current_event['notes'] = line[10:].strip()
        elif line.startswith('**Supporting Docs:**'):
            current_event['supporting_docs'] = line[18:].strip()

    if current_event:
        events.append(current_event)

    return events