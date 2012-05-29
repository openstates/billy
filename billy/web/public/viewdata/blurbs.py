from django.template.loader import render_to_string


def bio_blurb(legislator):
    if legislator['active']:
        return render_to_string('billy/web/public/bio_blurb.html',
                                dict(legislator=legislator))
    else:
        raise NotImplementedError('Bio blurbs for inactive legislators don\t work yet.')
        for role in legislator.old_roles_manager():
            import pdb;pdb.set_trace()
        return render_to_string('billy/web/public/bio_blurb_inactive.html',
                                dict(legislator=legislator))

