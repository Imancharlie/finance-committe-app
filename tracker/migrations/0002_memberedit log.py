# Generated migration for MemberEditLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MemberEditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_changed', models.CharField(max_length=50)),
                ('before_value', models.TextField(blank=True, null=True)),
                ('after_value', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edit_logs', to='tracker.member')),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='member_edit_logs', to='tracker.organization')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='membereditlog',
            index=models.Index(fields=['organization', 'created_at'], name='tracker_mem_organiz_idx'),
        ),
        migrations.AddIndex(
            model_name='membereditlog',
            index=models.Index(fields=['organization', 'member'], name='tracker_mem_organiz_member_idx'),
        ),
    ]
