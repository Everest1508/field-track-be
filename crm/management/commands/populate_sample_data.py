from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from crm.models import UserProfile, Customer, Lead, FieldVisit, FollowUp, Task


class Command(BaseCommand):
    help = 'Populate sample data for sales executives'

    def add_arguments(self, parser):
        parser.add_argument(
            '--executives',
            type=int,
            default=3,
            help='Number of sales executives to create',
        )
        parser.add_argument(
            '--customers',
            type=int,
            default=20,
            help='Number of customers to create',
        )
        parser.add_argument(
            '--visits',
            type=int,
            default=50,
            help='Number of field visits to create',
        )
        parser.add_argument(
            '--leads',
            type=int,
            default=30,
            help='Number of leads to create',
        )
        parser.add_argument(
            '--tasks',
            type=int,
            default=25,
            help='Number of tasks to create',
        )
        parser.add_argument(
            '--admin',
            action='store_true',
            help='Create admin user',
        )

    def handle(self, *args, **options):
        num_executives = options['executives']
        num_customers = options['customers']
        num_visits = options['visits']
        num_leads = options['leads']
        num_tasks = options['tasks']
        create_admin = options['admin']

        self.stdout.write('Creating sample data...')
        
        # Create admin user if requested
        admin_user = None
        if create_admin:
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@example.com',
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(self.style.SUCCESS('Created admin user: admin (password: admin123)'))
            
            # Ensure admin profile exists
            admin_profile, _ = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'role': 'admin',
                    'phone': '+1234567890',
                    'is_active': True,
                }
            )

        # Create or get sales executives
        executives = []
        for i in range(1, num_executives + 1):
            username = f'sales_exec_{i}'
            email = f'sales{i}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Sales',
                    'last_name': f'Executive {i}',
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
            
            # Ensure profile exists
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'sales_executive',
                    'phone': f'+123456789{i}',
                    'is_active': True,
                }
            )
            executives.append(user)

        # Create customers
        customers = []
        companies = [
            'Tech Solutions Inc', 'Global Industries', 'Digital Services Co',
            'Innovation Labs', 'Smart Systems Ltd', 'Future Tech Corp',
            'Advanced Solutions', 'Modern Enterprises', 'NextGen Technologies',
            'Cloud Services Inc', 'Data Analytics Co', 'AI Innovations',
            'Software Solutions', 'Hardware Systems', 'Network Services',
            'Security Solutions', 'Mobile Apps Co', 'Web Services Ltd',
            'Consulting Group', 'Business Solutions'
        ]
        
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa', 'James', 'Maria']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']

        for i in range(num_customers):
            customer, created = Customer.objects.get_or_create(
                name=f"{random.choice(first_names)} {random.choice(last_names)}",
                defaults={
                    'phone': f'+1{random.randint(2000000000, 9999999999)}',
                    'email': f'customer{i+1}@example.com',
                    'company': random.choice(companies),
                    'address': f'{random.randint(100, 9999)} Main St, City {i+1}',
                    'created_by': random.choice(executives),
                }
            )
            if created:
                customers.append(customer)
                self.stdout.write(self.style.SUCCESS(f'Created customer: {customer.name}'))

        # Create field visits
        visit_purposes = [
            'Product demonstration', 'Sales pitch', 'Follow-up meeting',
            'Contract discussion', 'Technical consultation', 'Customer support',
            'New product launch', 'Partnership discussion', 'Service review',
            'Account management'
        ]
        
        discussion_statuses = [
            'interested', 'not_interested', 'quotation_requested',
            'negotiation_ongoing', 'deal_closed', 'follow_up_required'
        ]

        for i in range(num_visits):
            visit_date = timezone.now() - timedelta(days=random.randint(0, 90))
            visit = FieldVisit.objects.create(
                customer=random.choice(customers),
                sales_executive=random.choice(executives),
                visit_date=visit_date,
                purpose=random.choice(visit_purposes),
                notes=f'Sample visit notes {i+1}. Discussed product features and pricing.',
                discussion_status=random.choice(discussion_statuses),
                latitude=round(random.uniform(40.0, 45.0), 6),
                longitude=round(random.uniform(-75.0, -70.0), 6),
            )
            if i % 10 == 0:
                self.stdout.write(self.style.SUCCESS(f'Created {i+1} visits...'))

        # Create leads
        lead_statuses = [
            'interested', 'quotation_requested', 'negotiation_ongoing',
            'deal_closed', 'not_interested'
        ]

        for i in range(num_leads):
            lead = Lead.objects.create(
                customer=random.choice(customers),
                sales_executive=random.choice(executives),
                status=random.choice(lead_statuses),
                notes=f'Lead notes {i+1}. Customer showed interest in our services.',
            )
            if i % 10 == 0:
                self.stdout.write(self.style.SUCCESS(f'Created {i+1} leads...'))

        # Create follow-ups
        for i in range(min(20, num_leads)):
            lead = Lead.objects.filter(status__in=['interested', 'quotation_requested', 'negotiation_ongoing']).first()
            if lead:
                due_date = timezone.now() + timedelta(days=random.randint(1, 30))
                FollowUp.objects.create(
                    lead=lead,
                    customer=lead.customer,
                    sales_executive=lead.sales_executive,
                    due_date=due_date,
                    notes=f'Follow-up reminder for {lead.customer.name}',
                    completed=random.choice([True, False]),
                )

        # Create tasks
        task_types = ['visit', 'followup', 'lead_contact', 'other']
        task_priorities = ['low', 'medium', 'high', 'urgent']
        task_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        task_titles = [
            'Schedule visit with customer', 'Follow up on quotation', 'Contact new lead',
            'Prepare presentation', 'Send product catalog', 'Schedule demo',
            'Review contract terms', 'Update customer information', 'Schedule follow-up call',
            'Prepare proposal', 'Visit potential client', 'Send pricing information'
        ]

        # Get admin user for assigning tasks
        admin_for_tasks = admin_user if admin_user else User.objects.filter(is_superuser=True).first()
        if not admin_for_tasks:
            admin_for_tasks = executives[0] if executives else None

        for i in range(num_tasks):
            task_customer = random.choice(customers) if customers else None
            task_lead = random.choice(list(Lead.objects.all()[:10])) if Lead.objects.exists() else None
            task_visit = random.choice(list(FieldVisit.objects.all()[:10])) if FieldVisit.objects.exists() else None
            
            due_date = timezone.now() + timedelta(days=random.randint(1, 60))
            task = Task.objects.create(
                title=random.choice(task_titles),
                description=f'Task description {i+1}. Complete this task as assigned.',
                task_type=random.choice(task_types),
                priority=random.choice(task_priorities),
                status=random.choice(task_statuses),
                assigned_to=random.choice(executives) if executives else None,
                assigned_by=admin_for_tasks,
                customer=task_customer,
                company=task_customer.company if task_customer else random.choice(companies) if companies else '',
                lead=task_lead,
                field_visit=task_visit if random.choice([True, False]) else None,
                due_date=due_date,
            )
            if i % 10 == 0:
                self.stdout.write(self.style.SUCCESS(f'Created {i+1} tasks...'))

        summary_lines = [
            f'\nSuccessfully created:',
            f'- {len(executives)} sales executives',
            f'- {len(customers)} customers',
            f'- {num_visits} field visits',
            f'- {num_leads} leads',
            f'- {min(20, num_leads)} follow-ups',
            f'- {num_tasks} tasks',
        ]
        
        if create_admin and admin_user:
            summary_lines.append(f'\nAdmin user created:')
            summary_lines.append(f'Username: admin')
            summary_lines.append(f'Password: admin123')
            summary_lines.append(f'Email: admin@example.com')
        
        summary_lines.extend([
            f'\nLogin credentials for sales executives:',
            f'Username: sales_exec_1, sales_exec_2, sales_exec_3',
            f'Password: password123',
            f'Email: sales1@example.com, sales2@example.com, sales3@example.com'
        ])

        self.stdout.write(self.style.SUCCESS('\n'.join(summary_lines)))

