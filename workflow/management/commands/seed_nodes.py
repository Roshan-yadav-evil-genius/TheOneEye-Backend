from django.core.management.base import BaseCommand
from django.utils import timezone
from workflow.models import StandaloneNode, NodeGroup
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Seed the database with default nodes data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing nodes',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        
        # Get or create NodeGroups for category mapping
        category_to_group_mapping = {
            'system': 'System Operations',
            'email': 'Email & Communication',
            'database': 'Database Operations',
            'api': 'API & Integration',
            'logic': 'Logic & Control Flow',
            'control': 'Workflow Control',
            'file': 'File Operations'
        }
        
        # Ensure all NodeGroups exist
        node_groups = {}
        for category, group_name in category_to_group_mapping.items():
            node_group, created = NodeGroup.objects.get_or_create(
                name=group_name,
                defaults={'is_active': True}
            )
            node_groups[category] = node_group
        
        # Mock nodes data from frontend
        mock_nodes_data = [
            # System nodes
            {
                'name': 'Start',
                'type': 'trigger',
                'category': 'system',
                'description': 'Initiates the workflow execution',
                'version': '1.0.0',
                'is_active': True,
                'created_by': 'system',
                'form_configuration': {},
                'tags': ['core', 'workflow']
            },
            {
                'name': 'End',
                'type': 'trigger',
                'category': 'system',
                'description': 'Terminates the workflow execution',
                'version': '1.0.0',
                'is_active': True,
                'created_by': 'system',
                'form_configuration': {},
                'tags': ['core', 'workflow']
            },
            
            # Email nodes
            {
                'name': 'Send Email',
                'type': 'action',
                'category': 'email',
                'description': 'Sends email notifications to recipients',
                'version': '1.2.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['communication', 'notification']
            },
            {
                'name': 'Email Listener',
                'type': 'trigger',
                'category': 'email',
                'description': 'Listens for incoming emails',
                'version': '1.1.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['communication', 'listener']
            },
            {
                'name': 'Email Template',
                'type': 'action',
                'category': 'email',
                'description': 'Uses predefined email templates',
                'version': '1.3.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['communication', 'template']
            },
            
            # Database nodes
            {
                'name': 'Database Query',
                'type': 'action',
                'category': 'database',
                'description': 'Executes SQL queries on connected databases',
                'version': '2.0.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'sql', 'query']
            },
            {
                'name': 'Database Insert',
                'type': 'action',
                'category': 'database',
                'description': 'Inserts data into database tables',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'sql', 'insert']
            },
            {
                'name': 'Database Update',
                'type': 'action',
                'category': 'database',
                'description': 'Updates existing database records',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'sql', 'update']
            },
            {
                'name': 'Database Delete',
                'type': 'action',
                'category': 'database',
                'description': 'Deletes records from database',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'sql', 'delete']
            },
            {
                'name': 'Database Transaction',
                'type': 'action',
                'category': 'database',
                'description': 'Manages database transactions',
                'version': '1.6.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'transaction']
            },
            {
                'name': 'Database Backup',
                'type': 'action',
                'category': 'database',
                'description': 'Creates database backups',
                'version': '1.4.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['database', 'backup', 'maintenance']
            },
            
            # API nodes
            {
                'name': 'API Call',
                'type': 'action',
                'category': 'api',
                'description': 'Makes HTTP requests to external APIs',
                'version': '2.1.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'http', 'integration']
            },
            {
                'name': 'Webhook',
                'type': 'trigger',
                'category': 'api',
                'description': 'Receives webhook notifications',
                'version': '1.7.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'webhook', 'listener']
            },
            {
                'name': 'REST API',
                'type': 'action',
                'category': 'api',
                'description': 'Makes RESTful API calls',
                'version': '1.8.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'rest', 'http']
            },
            {
                'name': 'GraphQL API',
                'type': 'action',
                'category': 'api',
                'description': 'Makes GraphQL API calls',
                'version': '1.9.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'graphql', 'query']
            },
            {
                'name': 'SOAP API',
                'type': 'action',
                'category': 'api',
                'description': 'Makes SOAP web service calls',
                'version': '1.3.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'soap', 'webservice']
            },
            {
                'name': 'OAuth Authentication',
                'type': 'action',
                'category': 'api',
                'description': 'Handles OAuth authentication flow',
                'version': '2.0.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['api', 'oauth', 'authentication']
            },
            
            # Logic nodes
            {
                'name': 'Condition',
                'type': 'logic',
                'category': 'logic',
                'description': 'Evaluates conditions and branches workflow',
                'version': '1.4.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'condition', 'branching']
            },
            {
                'name': 'Switch',
                'type': 'logic',
                'category': 'logic',
                'description': 'Multi-way conditional branching',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'switch', 'branching']
            },
            {
                'name': 'Loop',
                'type': 'logic',
                'category': 'logic',
                'description': 'Repeats actions for multiple items',
                'version': '1.6.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'loop', 'iteration']
            },
            {
                'name': 'Merge',
                'type': 'logic',
                'category': 'logic',
                'description': 'Merges multiple data streams',
                'version': '1.7.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'merge', 'data']
            },
            {
                'name': 'Split',
                'type': 'logic',
                'category': 'logic',
                'description': 'Splits data into multiple streams',
                'version': '1.8.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'split', 'data']
            },
            {
                'name': 'Aggregate',
                'type': 'logic',
                'category': 'logic',
                'description': 'Aggregates data from multiple sources',
                'version': '1.9.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['logic', 'aggregate', 'data']
            },
            
            # Control nodes
            {
                'name': 'Delay',
                'type': 'action',
                'category': 'control',
                'description': 'Pauses workflow execution for specified time',
                'version': '1.2.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['control', 'delay', 'timing']
            },
            {
                'name': 'Schedule',
                'type': 'trigger',
                'category': 'control',
                'description': 'Triggers workflow at scheduled times',
                'version': '1.3.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['control', 'schedule', 'timing']
            },
            {
                'name': 'Retry',
                'type': 'action',
                'category': 'control',
                'description': 'Retries failed operations',
                'version': '1.4.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['control', 'retry', 'error-handling']
            },
            {
                'name': 'Timeout',
                'type': 'action',
                'category': 'control',
                'description': 'Sets timeout for operations',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['control', 'timeout', 'error-handling']
            },
            {
                'name': 'Parallel',
                'type': 'logic',
                'category': 'control',
                'description': 'Executes operations in parallel',
                'version': '1.6.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['control', 'parallel', 'performance']
            },
            
            # File nodes
            {
                'name': 'File Read',
                'type': 'action',
                'category': 'file',
                'description': 'Reads content from files',
                'version': '1.3.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'read', 'io']
            },
            {
                'name': 'File Write',
                'type': 'action',
                'category': 'file',
                'description': 'Writes content to files',
                'version': '1.3.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'write', 'io']
            },
            {
                'name': 'File Process',
                'type': 'action',
                'category': 'file',
                'description': 'Processes and transforms files',
                'version': '1.4.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'process', 'transform']
            },
            {
                'name': 'File Upload',
                'type': 'action',
                'category': 'file',
                'description': 'Uploads files to cloud storage',
                'version': '1.5.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'upload', 'cloud']
            },
            {
                'name': 'File Download',
                'type': 'action',
                'category': 'file',
                'description': 'Downloads files from remote sources',
                'version': '1.6.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'download', 'remote']
            },
            {
                'name': 'File Compress',
                'type': 'action',
                'category': 'file',
                'description': 'Compresses files to reduce size',
                'version': '1.7.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'compress', 'optimization']
            },
            {
                'name': 'File Extract',
                'type': 'action',
                'category': 'file',
                'description': 'Extracts files from archives',
                'version': '1.8.0',
                'is_active': True,
                'created_by': 'admin',
                'form_configuration': {},
                'tags': ['file', 'extract', 'archive']
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for node_data in mock_nodes_data:
            # Add node_group to the node data
            category = node_data['category']
            if category in node_groups:
                node_data['node_group'] = node_groups[category]
            
            # Check if node already exists
            existing_node = StandaloneNode.objects.filter(
                name=node_data['name'],
                type=node_data['type'],
                category=node_data['category']
            ).first()

            if existing_node:
                if force:
                    # Update existing node
                    for key, value in node_data.items():
                        setattr(existing_node, key, value)
                    existing_node.updated_at = timezone.now()
                    
                    if not dry_run:
                        existing_node.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated: {existing_node.name}')
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Skipped (exists): {node_data["name"]}')
                    )
            else:
                # Create new node
                if not dry_run:
                    StandaloneNode.objects.create(**node_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {node_data["name"]}')
                )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SEEDING SUMMARY')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        
        self.stdout.write(f'Created: {created_count} nodes')
        self.stdout.write(f'Updated: {updated_count} nodes')
        self.stdout.write(f'Skipped: {skipped_count} nodes')
        self.stdout.write(f'Total processed: {len(mock_nodes_data)} nodes')
        
        if not dry_run:
            total_nodes = StandaloneNode.objects.count()
            self.stdout.write(f'Total nodes in database: {total_nodes}')
            
            self.stdout.write(
                self.style.SUCCESS('\n✅ Database seeding completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️  This was a dry run. Use --force to actually create/update nodes.')
            )
