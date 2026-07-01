from django.db import migrations


def seed(apps, schema_editor):
    Hero = apps.get_model("landing_cms", "HeroContent")
    About = apps.get_model("landing_cms", "AboutContent")
    Settings_ = apps.get_model("landing_cms", "SiteSettings")
    Hero.objects.update_or_create(pk=1, defaults={
        "title_es": "Soporte que no se hace esperar.",
        "title_en": "Support that won't keep you waiting.",
        "subtitle_es": "La plataforma de help-desk para tu equipo.",
        "subtitle_en": "The help-desk platform for your team.",
    })
    About.objects.update_or_create(pk=1, defaults={
        "mission_es": "Edita esta misión en el admin.",
        "mission_en": "Edit this mission from the admin.",
        "vision_es": "Edita esta visión en el admin.",
        "vision_en": "Edit this vision from the admin.",
    })
    Settings_.objects.update_or_create(pk=1, defaults={})


def unseed(apps, schema_editor):
    # leave data on rollback; nothing to do
    pass


class Migration(migrations.Migration):
    dependencies = [("landing_cms", "0002_feature_location_teammember")]
    operations = [migrations.RunPython(seed, unseed)]
