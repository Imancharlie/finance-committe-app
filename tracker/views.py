from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Count, F
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from decimal import Decimal, InvalidOperation
import json
import openpyxl
from io import BytesIO
from django.db import connection
from django.utils import timezone

from .models import Member, Transaction
from .forms import CustomLoginForm, MemberForm, QuickMemberForm, TransactionForm, MemberUpdateForm, ExcelImportForm


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('tracker:dashboard')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('tracker:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'tracker/login.html', {'form': form})


@login_required
def dashboard(request):
    """Main dashboard with member table and statistics"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    filter_status = request.GET.get('filter', '')
    
    # Initialize default values
    total_collected = Decimal('0.00')
    total_pledged = Decimal('0.00')
    target_amount = Decimal('11000000.00')  # 11M target
    progress_percentage = 0
    not_paid_count = 0
    incomplete_count = 0
    complete_count = 0
    exceeded_count = 0
    page_obj = None
    members = []
    
    try:
        # Get all members with individual error handling
        members = []
        try:
            # Try to get all members at once
            all_members = Member.objects.all()
            for member in all_members:
                try:
                    # Verify each member's decimal fields are valid
                    if member.pledge is None or member.paid_total is None:
                        # Fix invalid values
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                    
                    members.append(member)
                except Exception as e:
                    # Skip problematic members
                    continue
        except Exception as e:
            # If bulk query fails, get members one by one
            try:
                member_ids = Member.objects.values_list('id', flat=True)
                for member_id in member_ids:
                    try:
                        member = Member.objects.get(id=member_id)
                        # Fix any invalid decimal values
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                        members.append(member)
                    except:
                        continue
            except:
                members = []
        
        # Apply search filter
        if search_query and members:
            filtered_members = []
            for member in members:
                try:
                    if (search_query.lower() in member.name.lower() or
                        (member.phone and search_query in member.phone) or
                        (member.email and search_query.lower() in member.email.lower())):
                        filtered_members.append(member)
                except:
                    continue
            members = filtered_members
        
        # Apply status filter
        if filter_status and members:
            filtered_members = []
            for member in members:
                try:
                    if filter_status == 'incomplete' and member.paid_total > 0 and member.paid_total < member.pledge:
                        filtered_members.append(member)
                    elif filter_status == 'complete' and member.paid_total >= member.pledge:
                        filtered_members.append(member)
                    elif filter_status == 'pledged' and member.pledge > 70000:
                        filtered_members.append(member)
                    elif filter_status == 'not_started' and member.paid_total == 0:
                        filtered_members.append(member)
                    elif filter_status == 'exceeded' and member.paid_total > member.pledge:
                        filtered_members.append(member)
                except:
                    continue
            members = filtered_members
        
        # Calculate statistics safely
        try:
            # Manual calculation to avoid aggregation issues
            total_collected = Decimal('0.00')
            total_pledged = Decimal('0.00')
            not_paid_count = 0
            incomplete_count = 0
            complete_count = 0
            exceeded_count = 0
            
            for member in members:
                try:
                    # Ensure we have valid decimal values
                    pledge = member.pledge if member.pledge is not None else Decimal('70000.00')
                    paid_total = member.paid_total if member.paid_total is not None else Decimal('0.00')
                    
                    total_pledged += pledge
                    total_collected += paid_total
                    
                    # Count by status
                    if paid_total == 0:
                        not_paid_count += 1
                    elif paid_total < pledge:
                        incomplete_count += 1
                    elif paid_total == pledge:
                        complete_count += 1
                    else:  # paid_total > pledge
                        exceeded_count += 1
                except:
                    # Skip problematic members
                    continue
            
        except Exception as e:
            # If calculation fails, use default values
            total_collected = Decimal('0.00')
            total_pledged = Decimal('0.00')
            not_paid_count = 0
            incomplete_count = 0
            complete_count = 0
            exceeded_count = 0
        
        # Calculate progress percentage
        progress_percentage = (total_collected / target_amount * 100) if target_amount > 0 else 0
        
        # Pagination with error handling
        try:
            # Create a simple list-based pagination to avoid queryset issues
            page_size = 20
            page_number = request.GET.get('page', 1)
            try:
                page_number = int(page_number)
            except:
                page_number = 1
            
            # Calculate pagination manually
            total_members = len(members)
            total_pages = (total_members + page_size - 1) // page_size
            
            # Ensure page number is valid
            if page_number < 1:
                page_number = 1
            elif page_number > total_pages and total_pages > 0:
                page_number = total_pages
            
            # Create a simple page object
            class SimplePage:
                def __init__(self, object_list, number, paginator):
                    self.paginator = paginator
                    self.number = number
                    
                    # Calculate the slice for this page
                    start_index = (number - 1) * paginator.per_page
                    end_index = start_index + paginator.per_page
                    self.object_list = object_list[start_index:end_index]
                
                def has_other_pages(self):
                    return self.paginator.num_pages > 1
                
                def has_previous(self):
                    return self.number > 1
                
                def has_next(self):
                    return self.number < self.paginator.num_pages
                
                def previous_page_number(self):
                    return self.number - 1
                
                def next_page_number(self):
                    return self.number + 1
            
            class SimplePaginator:
                def __init__(self, object_list, per_page):
                    self.object_list = object_list
                    self.per_page = per_page
                    self.count = len(object_list)
                    self.num_pages = (self.count + per_page - 1) // per_page
                
                def get_page(self, number):
                    return SimplePage(self.object_list, number, self)
            
            paginator = SimplePaginator(members, page_size)
            page_obj = paginator.get_page(page_number)
            
        except Exception as e:
            # If pagination fails, create empty page
            page_obj = None
            members = []
        
    except Exception as e:
        # If everything fails, use default values
        pass
    
    context = {
        'page_obj': page_obj,
        'members': page_obj.object_list if page_obj else [],
        'search_query': search_query,
        'filter_status': filter_status,
        'total_collected': total_collected,
        'total_pledged': total_pledged,
        'target_amount': target_amount,
        'progress_percentage': progress_percentage,
        'not_paid_count': not_paid_count,
        'incomplete_count': incomplete_count,
        'complete_count': complete_count,
        'exceeded_count': exceeded_count,
        'quick_member_form': QuickMemberForm(),
        'excel_import_form': ExcelImportForm(),
    }
    
    return render(request, 'tracker/dashboard.html', context)


@login_required
def member_detail(request, member_id):
    """Member detail page with transaction history"""
    try:
        member = get_object_or_404(Member, id=member_id)
        transactions = member.transaction_set.all().order_by('-date', '-id')
        
        if request.method == 'POST':
            transaction_form = TransactionForm(request.POST)
            if transaction_form.is_valid():
                try:
                    # Get the amount and validate it
                    amount = transaction_form.cleaned_data['amount']
                    
                    # Validate amount is positive
                    if amount <= 0:
                        messages.error(request, 'Payment amount must be greater than zero.')
                        transaction_form = TransactionForm(request.POST)  # Re-populate form
                    else:
                        # Create the transaction
                        transaction = transaction_form.save(commit=False)
                        transaction.member = member
                        transaction.added_by = request.user
                        
                        # Set date to today if not provided
                        if not transaction.date:
                            from datetime import date
                            transaction.date = date.today()
                        
                        # Save the transaction
                        transaction.save()
                        
                        # Update member's paid_total
                        try:
                            # Recalculate paid_total from all transactions
                            total_paid = member.transaction_set.aggregate(
                                total=Sum('amount')
                            )['total'] or Decimal('0.00')
                            
                            member.paid_total = total_paid
                            member.save()
                            
                            messages.success(request, f'Payment of TZS {amount:,.0f} recorded successfully!')
                            return redirect('tracker:member_detail', member_id=member.id)
                            
                        except Exception as e:
                            # If updating paid_total fails, still save the transaction
                            messages.warning(request, f'Payment recorded but there was an issue updating member totals. Please contact administrator.')
                            return redirect('tracker:member_detail', member_id=member.id)
                            
                except Exception as e:
                    messages.error(request, f'Error recording payment: {str(e)}')
                    transaction_form = TransactionForm(request.POST)  # Re-populate form
            else:
                # Form validation errors
                for field, errors in transaction_form.errors.items():
                    for error in errors:
                        field_name = transaction_form.fields[field].label or field
                        messages.error(request, f'{field_name}: {error}')
        else:
            transaction_form = TransactionForm()
        
        context = {
            'member': member,
            'transactions': transactions,
            'transaction_form': transaction_form,
            'member_form': MemberForm(instance=member),
        }
        
        return render(request, 'tracker/member_detail.html', context)
        
    except Member.DoesNotExist:
        messages.error(request, 'Member not found.')
        return redirect('tracker:dashboard')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')
        return redirect('tracker:dashboard')


@login_required
def add_member(request):
    """Add new member"""
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Member "{member.name}" added successfully!')
            return redirect('tracker:member_detail', member_id=member.id)
    else:
        form = MemberForm()
    
    return render(request, 'tracker/add_member.html', {'form': form})


@login_required
def edit_member(request, member_id):
    """Edit member details"""
    member = get_object_or_404(Member, id=member_id)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'Member "{member.name}" updated successfully!')
            return redirect('tracker:member_detail', member_id=member.id)
    else:
        form = MemberForm(instance=member)
    
    return render(request, 'tracker/edit_member.html', {'form': form, 'member': member})


@login_required
def import_excel(request):
    """Import members from Excel file"""
    if request.method == 'POST':
        form = ExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = form.cleaned_data['excel_file']
            update_existing = form.cleaned_data['update_existing']
            default_pledge = form.cleaned_data['default_pledge']
            
            try:
                # Read Excel file
                workbook = openpyxl.load_workbook(BytesIO(excel_file.read()))
                sheet = workbook.active
                
                created_count = 0
                updated_count = 0
                errors = []
                
                # Skip header row and process data
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not row[0]:  # Skip empty rows
                        continue
                    
                    try:
                        name = str(row[0]).strip()
                        pledge = Decimal(str(row[1])) if row[1] else default_pledge
                        phone = str(row[2]).strip() if row[2] else ''
                        email = str(row[3]).strip() if row[3] else ''
                        course = str(row[4]).strip() if row[4] else ''
                        year = str(row[5]).strip() if row[5] else ''
                        
                        if update_existing:
                            member, created = Member.objects.update_or_create(
                                name=name,
                                defaults={
                                    'pledge': pledge,
                                    'phone': phone if phone else None,
                                    'email': email if email else None,
                                    'course': course if course else None,
                                    'year': year if year else None,
                                }
                            )
                            if created:
                                created_count += 1
                            else:
                                updated_count += 1
                        else:
                            # Only create new members
                            if not Member.objects.filter(name=name).exists():
                                Member.objects.create(
                                    name=name,
                                    pledge=pledge,
                                    phone=phone if phone else None,
                                    email=email if email else None,
                                    course=course if course else None,
                                    year=year if year else None,
                                )
                                created_count += 1
                            else:
                                errors.append(f"Member '{name}' already exists")
                        
                    except Exception as e:
                        errors.append(f"Error processing row with name '{row[0]}': {str(e)}")
                
                # Show results
                if created_count > 0:
                    messages.success(request, f'Successfully created {created_count} new members!')
                if updated_count > 0:
                    messages.info(request, f'Updated {updated_count} existing members!')
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        messages.warning(request, error)
                    if len(errors) > 5:
                        messages.warning(request, f'... and {len(errors) - 5} more errors')
                
                return redirect('tracker:dashboard')
                
            except Exception as e:
                messages.error(request, f'Error reading Excel file: {str(e)}')
    else:
        form = ExcelImportForm()
    
    return render(request, 'tracker/import_excel.html', {'form': form})


@login_required
def admin_log(request):
    """Admin log showing all transactions"""
    transactions = Transaction.objects.select_related('member', 'added_by').all()
    
    # Apply filters
    boss_filter = request.GET.get('boss', '')
    date_filter = request.GET.get('date', '')
    amount_filter = request.GET.get('amount', '')
    
    if boss_filter:
        transactions = transactions.filter(added_by__username__icontains=boss_filter)
    if date_filter:
        transactions = transactions.filter(date=date_filter)
    if amount_filter:
        try:
            amount = Decimal(amount_filter)
            transactions = transactions.filter(amount=amount)
        except:
            pass
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transactions': page_obj,
        'boss_filter': boss_filter,
        'date_filter': date_filter,
        'amount_filter': amount_filter,
    }
    
    return render(request, 'tracker/admin_log.html', context)


# AJAX Views
@login_required
@require_POST
@csrf_exempt
def update_member_ajax(request):
    """AJAX endpoint for updating member data"""
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        field = data.get('field')
        value = data.get('value')
        
        member = get_object_or_404(Member, id=member_id)
        
        if field in ['pledge', 'paid_total']:
            try:
                # Clean the value and convert to Decimal
                if value is None or value == '':
                    value = Decimal('0.00')
                else:
                    # Remove any non-numeric characters except decimal point
                    cleaned_value = str(value).replace(',', '').strip()
                    value = Decimal(cleaned_value)
                
                # Ensure value is not negative
                if value < 0:
                    value = Decimal('0.00')
                
                setattr(member, field, value)
                member.save()
                
                # Return updated member data
                return JsonResponse({
                    'success': True,
                    'pledge': float(member.pledge),
                    'paid_total': float(member.paid_total),
                    'remaining': float(member.remaining),
                    'is_complete': member.is_complete,
                    'is_incomplete': member.is_incomplete,
                    'not_started': member.not_started,
                    'has_exceeded': member.has_exceeded,
                    'status_display': member.status_display,
                })
            except (ValueError, TypeError, InvalidOperation) as e:
                return JsonResponse({'success': False, 'error': f'Invalid value: {str(e)}'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid field'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
@csrf_exempt
def add_member_ajax(request):
    """AJAX endpoint for quick member addition"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        pledge = data.get('pledge', 70000)
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})
        
        # Check if member already exists
        if Member.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Member already exists'})
        
        member = Member.objects.create(
            name=name,
            pledge=Decimal(pledge)
        )
        
        # Return the new member data
        return JsonResponse({
            'success': True,
            'member': {
                'id': member.id,
                'name': member.name,
                'pledge': float(member.pledge),
                'paid_total': float(member.paid_total),
                'remaining': float(member.remaining),
                'status_display': member.status_display,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
@csrf_exempt
def update_transaction_note_ajax(request):
    """AJAX endpoint for updating transaction notes"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        note = data.get('note', '')
        
        transaction = get_object_or_404(Transaction, id=transaction_id)
        transaction.note = note
        transaction.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def daily_collection(request):
    """Daily collection page for recording payments"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    filter_status = request.GET.get('filter', '')
    
    # Initialize default values
    total_collected = Decimal('0.00')
    total_pledged = Decimal('0.00')
    target_amount = Decimal('11000000.00')  # 11M target
    progress_percentage = 0
    not_paid_count = 0
    incomplete_count = 0
    complete_count = 0
    exceeded_count = 0
    page_obj = None
    members = []
    
    try:
        # Get all members with individual error handling
        members = []
        try:
            # Try to get all members at once
            all_members = Member.objects.all()
            for member in all_members:
                try:
                    # Verify each member's decimal fields are valid
                    if member.pledge is None or member.paid_total is None:
                        # Fix invalid values
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                    
                    members.append(member)
                except Exception as e:
                    # Skip problematic members
                    continue
        except Exception as e:
            # If bulk query fails, get members one by one
            try:
                member_ids = Member.objects.values_list('id', flat=True)
                for member_id in member_ids:
                    try:
                        member = Member.objects.get(id=member_id)
                        # Fix any invalid decimal values
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                        members.append(member)
                    except:
                        continue
            except:
                members = []
        
        # Apply search filter
        if search_query and members:
            filtered_members = []
            for member in members:
                try:
                    if (search_query.lower() in member.name.lower() or
                        (member.phone and search_query in member.phone) or
                        (member.email and search_query.lower() in member.email.lower())):
                        filtered_members.append(member)
                except:
                    continue
            members = filtered_members
        
        # Apply status filter
        if filter_status and members:
            filtered_members = []
            for member in members:
                try:
                    if filter_status == 'incomplete' and member.paid_total > 0 and member.paid_total < member.pledge:
                        filtered_members.append(member)
                    elif filter_status == 'complete' and member.paid_total >= member.pledge:
                        filtered_members.append(member)
                    elif filter_status == 'pledged' and member.pledge > 70000:
                        filtered_members.append(member)
                    elif filter_status == 'not_started' and member.paid_total == 0:
                        filtered_members.append(member)
                    elif filter_status == 'exceeded' and member.paid_total > member.pledge:
                        filtered_members.append(member)
                except:
                    continue
            members = filtered_members
        
        # Calculate statistics safely
        try:
            # Manual calculation to avoid aggregation issues
            total_collected = Decimal('0.00')
            total_pledged = Decimal('0.00')
            not_paid_count = 0
            incomplete_count = 0
            complete_count = 0
            exceeded_count = 0
            
            for member in members:
                try:
                    # Ensure we have valid decimal values
                    pledge = member.pledge if member.pledge is not None else Decimal('70000.00')
                    paid_total = member.paid_total if member.paid_total is not None else Decimal('0.00')
                    
                    total_pledged += pledge
                    total_collected += paid_total
                    
                    # Count by status
                    if paid_total == 0:
                        not_paid_count += 1
                    elif paid_total < pledge:
                        incomplete_count += 1
                    elif paid_total == pledge:
                        complete_count += 1
                    else:  # paid_total > pledge
                        exceeded_count += 1
                except:
                    # Skip problematic members
                    continue
            
        except Exception as e:
            # If calculation fails, use default values
            total_collected = Decimal('0.00')
            total_pledged = Decimal('0.00')
            not_paid_count = 0
            incomplete_count = 0
            complete_count = 0
            exceeded_count = 0
        
        # Calculate progress percentage
        progress_percentage = (total_collected / target_amount * 100) if target_amount > 0 else 0
        
        # Pagination with error handling
        try:
            # Create a simple list-based pagination to avoid queryset issues
            page_size = 20
            page_number = request.GET.get('page', 1)
            try:
                page_number = int(page_number)
            except:
                page_number = 1
            
            # Calculate pagination manually
            total_members = len(members)
            total_pages = (total_members + page_size - 1) // page_size
            
            # Ensure page number is valid
            if page_number < 1:
                page_number = 1
            elif page_number > total_pages and total_pages > 0:
                page_number = total_pages
            
            # Create a simple page object
            class SimplePage:
                def __init__(self, object_list, number, paginator):
                    self.paginator = paginator
                    self.number = number
                    
                    # Calculate the slice for this page
                    start_index = (number - 1) * paginator.per_page
                    end_index = start_index + paginator.per_page
                    self.object_list = object_list[start_index:end_index]
                
                def has_other_pages(self):
                    return self.paginator.num_pages > 1
                
                def has_previous(self):
                    return self.number > 1
                
                def has_next(self):
                    return self.number < self.paginator.num_pages
                
                def previous_page_number(self):
                    return self.number - 1
                
                def next_page_number(self):
                    return self.number + 1
            
            class SimplePaginator:
                def __init__(self, object_list, per_page):
                    self.object_list = object_list
                    self.per_page = per_page
                    self.count = len(object_list)
                    self.num_pages = (self.count + per_page - 1) // per_page
                
                def get_page(self, number):
                    return SimplePage(self.object_list, number, self)
            
            paginator = SimplePaginator(members, page_size)
            page_obj = paginator.get_page(page_number)
            
        except Exception as e:
            # If pagination fails, create empty page
            page_obj = None
            members = []
        
    except Exception as e:
        # If everything fails, use default values
        pass
    
    context = {
        'page_obj': page_obj,
        'members': page_obj.object_list if page_obj else [],
        'search_query': search_query,
        'filter_status': filter_status,
        'total_collected': total_collected,
        'total_pledged': total_pledged,
        'target_amount': target_amount,
        'progress_percentage': progress_percentage,
        'not_paid_count': not_paid_count,
        'incomplete_count': incomplete_count,
        'complete_count': complete_count,
        'exceeded_count': exceeded_count,
        'today': timezone.now().date(),
    }
    
    return render(request, 'tracker/daily_collection.html', context)


@login_required
@require_POST
@csrf_exempt
def record_daily_payment_ajax(request):
    """AJAX endpoint for recording daily payments"""
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        payment_amount = data.get('payment_amount')
        note = data.get('note', '')
        
        if not member_id or not payment_amount:
            return JsonResponse({'success': False, 'error': 'Member ID and payment amount are required'})
        
        # Get member
        member = get_object_or_404(Member, id=member_id)
        
        # Convert payment amount to decimal
        try:
            payment_amount = Decimal(str(payment_amount).replace(',', '').strip())
            if payment_amount <= 0:
                return JsonResponse({'success': False, 'error': 'Payment amount must be greater than 0'})
        except (ValueError, InvalidOperation):
            return JsonResponse({'success': False, 'error': 'Invalid payment amount'})
        
        # Create transaction
        transaction = Transaction.objects.create(
            member=member,
            amount=payment_amount,
            date=timezone.now().date(),
            added_by=request.user,
            note=note
        )
        
        # Update member's paid_total (this happens automatically via the model's save method)
        member.refresh_from_db()
        
        # Return updated member data
        return JsonResponse({
            'success': True,
            'transaction_id': transaction.id,
            'member': {
                'id': member.id,
                'name': member.name,
                'pledge': float(member.pledge),
                'paid_total': float(member.paid_total),
                'remaining': float(member.remaining),
                'is_complete': member.is_complete,
                'is_incomplete': member.is_incomplete,
                'not_started': member.not_started,
                'has_exceeded': member.has_exceeded,
                'status_display': member.status_display,
            },
            'message': f'Payment of TZS {payment_amount:,.0f} recorded successfully!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def offline_view(request):
    """Offline page for PWA"""
    return render(request, 'offline.html')
