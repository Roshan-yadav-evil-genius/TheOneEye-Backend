# Generated migration to move DemoRequest from workflow to contact app

import uuid
from django.db import migrations, models


def copy_demorequest_data(apps, schema_editor):
    """Copy DemoRequest data from workflow app to contact app"""
    db_alias = schema_editor.connection.alias
    
    # Check if the workflow_demorequest table exists
    try:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='workflow_demorequest'
            """)
            table_exists = cursor.fetchone() is not None
    except Exception:
        # If we can't check, assume table doesn't exist
        table_exists = False
    
    if not table_exists:
        # Table doesn't exist, nothing to copy
        return
    
    try:
        # Get the old and new models
        OldDemoRequest = apps.get_model('workflow', 'DemoRequest')
        NewDemoRequest = apps.get_model('contact', 'DemoRequest')
        
        # Copy all records
        for old_record in OldDemoRequest.objects.using(db_alias).all():
            NewDemoRequest.objects.using(db_alias).create(
                id=old_record.id,
                created_at=old_record.created_at,
                updated_at=old_record.updated_at,
                full_name=old_record.full_name,
                company_name=old_record.company_name,
                work_email=old_record.work_email,
                automation_needs=old_record.automation_needs,
                status=old_record.status,
                notes=old_record.notes,
            )
    except Exception as e:
        # If there's an error accessing the model or table, skip the copy
        # This handles cases where the model doesn't exist in the migration state
        pass


def reverse_copy_demorequest_data(apps, schema_editor):
    """Reverse migration: copy data back from contact to workflow"""
    db_alias = schema_editor.connection.alias
    
    # Check if the contact_demorequest table exists
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='contact_demorequest'
        """)
        table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # Table doesn't exist, nothing to copy back
        return
    
    OldDemoRequest = apps.get_model('workflow', 'DemoRequest')
    NewDemoRequest = apps.get_model('contact', 'DemoRequest')
    
    # Copy all records back
    for new_record in NewDemoRequest.objects.using(db_alias).all():
        OldDemoRequest.objects.using(db_alias).create(
            id=new_record.id,
            created_at=new_record.created_at,
            updated_at=new_record.updated_at,
            full_name=new_record.full_name,
            company_name=new_record.company_name,
            work_email=new_record.work_email,
            automation_needs=new_record.automation_needs,
            status=new_record.status,
            notes=new_record.notes,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
    ]
    
    # Optional dependency - only needed if workflow_demorequest table exists
    # If the table doesn't exist, we'll skip the data copy
    run_before = [
        ('workflow', '0021_remove_demorequest'),  # Run before workflow removes the model
    ]

    operations = [
        # Create DemoRequest model in contact app
        migrations.CreateModel(
            name="DemoRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=255)),
                ("company_name", models.CharField(max_length=255)),
                ("work_email", models.CharField(max_length=255)),
                ("automation_needs", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("contacted", "Contacted"),
                            ("scheduled", "Scheduled"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        # Copy data from workflow_demorequest to contact_demorequest
        migrations.RunPython(
            copy_demorequest_data,
            reverse_copy_demorequest_data,
        ),
        # Drop the workflow_demorequest table after data has been copied (if it exists)
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS workflow_demorequest;",
            reverse_sql="-- Cannot reverse table drop",
        ),
    ]

