from django.template.loader import render_to_string


def bio_blurb(legislator):
    return render_to_string('billy/web/public/bio_blurb.html',
                            dict(legislator=legislator))
