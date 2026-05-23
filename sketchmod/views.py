from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def canvas(request):
    return render(request, "sketchmod/canvas.html")
