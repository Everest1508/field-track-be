from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from crm.models import UserProfile, Customer, Lead, FieldVisit, FollowUp


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

    def handle(self, *args, **options):
        num_executives = options['executives']
        num_customers = options['customers']
        num_visits = options['visits']
        num_leads = options['leads']

        self.stdout.write('Creating sample data...')

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

        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully created:\n'
            f'- {len(executives)} sales executives\n'
            f'- {len(customers)} customers\n'
            f'- {num_visits} field visits\n'
            f'- {num_leads} leads\n'
            f'- {min(20, num_leads)} follow-ups\n\n'
            f'Login credentials for sales executives:\n'
            f'Username: sales_exec_1, sales_exec_2, sales_exec_3\n'
            f'Password: password123\n'
            f'Email: sales1@example.com, sales2@example.com, sales3@example.com'
        ))

