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
from django.contrib.admin.views.decorators import staff_member_required

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
# Add these imports to your views.py file
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from decimal import Decimal
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from .models import Member, Transaction
from reportlab.platypus import PageBreak, KeepTogether
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
import json

from .models import Member, Transaction
from .forms import MemberForm, TransactionForm


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from decimal import Decimal
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, F
from django.db import models
from decimal import Decimal
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Member

@login_required
def edit_members(request):
    """Main view for editing member details with smart filtering"""
    try:
        # Get all members with all their information
        members = Member.objects.all().order_by('name').select_related()

        # Handle search (keep for backend if needed)
        search_query = request.GET.get('search', '').strip()
        if search_query:
            members = members.filter(
                Q(name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(course__icontains=search_query)
            )

        # Calculate statistics for quick stats
        total_members = Member.objects.count()

        # Calculate payment statistics using model properties
        all_members = Member.objects.all()
        completed_payments = 0
        incomplete_payments = 0
        not_started_payments = 0
        exceeded_payments = 0

        for member in all_members:
            if member.is_complete:
                completed_payments += 1
            elif member.is_incomplete:
                incomplete_payments += 1
            elif member.not_started:
                not_started_payments += 1
            elif member.has_exceeded:
                exceeded_payments += 1

        # Prepare members data with all fields and status information
        members_data = []
        for member in members:
            # Determine status for filtering
            if member.is_complete:
                status = 'complete'
                status_html = '<small class="status-complete">✓ Complete</small>'
            elif member.is_incomplete:
                status = 'incomplete'
                status_html = '<small class="status-incomplete">⚠ Incomplete</small>'
            elif member.not_started:
                status = 'not_started'
                status_html = '<small class="status-not-started">✗ Not Started</small>'
            elif member.has_exceeded:
                status = 'exceeded'
                status_html = '<small class="status-exceeded">↗ Exceeded</small>'
            else:
                status = 'unknown'
                status_html = '<small class="text-muted">-</small>'

            members_data.append({
                'id': member.id,
                'name': member.name,
                'phone': member.phone or '',
                'email': member.email or '',
                'course': member.course or '',
                'year_of_study': member.year or '',
                'pledge': member.pledge,
                'paid_total': member.paid_total,
                'remaining': member.remaining,
                'is_active': member.is_active,
                'status_display': member.status_display,
                'is_complete': member.is_complete,
                'is_incomplete': member.is_incomplete,
                'not_started': member.not_started,
                'has_exceeded': member.has_exceeded,
                'status': status,
                'status_html': status_html,
                'created_at': member.created_at,
                'updated_at': member.updated_at,
            })

        context = {
            'members': members_data,
            'search_query': search_query,
            'total_members': total_members,
            'completed_payments': completed_payments,
            'incomplete_payments': incomplete_payments,
            'not_started_payments': not_started_payments,
            'exceeded_payments': exceeded_payments,
            'can_edit': request.user.is_staff,  # Permission check
        }

        return render(request, 'tracker/Edit_Members_table.html', context)

    except Exception as e:
        messages.error(request, f'Error loading members: {str(e)}')
        return redirect('tracker:dashboard')

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def update_member_ajaxs(request):
    """AJAX endpoint for updating member details"""
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')

        if not member_id:
            return JsonResponse({'success': False, 'error': 'Member ID is required'})

        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Member not found'})

        # Update basic fields (always allowed)
        if 'name' in data:
            if not data['name'].strip():
                return JsonResponse({'success': False, 'error': 'Name cannot be empty'})
            member.name = data['name'].strip()

        if 'phone_number' in data:
            member.phone = data['phone_number'].strip()

        if 'year_of_study' in data:
            member.year = data['year_of_study'].strip()

        # Update paid amount only if user is staff
        if 'paid_total' in data and request.user.is_staff:
            try:
                paid_amount = float(data['paid_total'])
                if paid_amount < 0:
                    return JsonResponse({'success': False, 'error': 'Paid amount cannot be negative'})
                member.paid_total = paid_amount
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid paid amount'})

        member.save()

        # Calculate updated status for response
        if member.is_complete:
            status = 'complete'
            status_html = '<small class="status-complete">✓ Complete</small>'
        elif member.is_incomplete:
            status = 'incomplete'
            status_html = '<small class="status-incomplete">⚠ Incomplete</small>'
        elif member.not_started:
            status = 'not_started'
            status_html = '<small class="status-not-started">✗ Not Started</small>'
        elif member.has_exceeded:
            status = 'exceeded'
            status_html = '<small class="status-exceeded">↗ Exceeded</small>'
        else:
            status = 'unknown'
            status_html = '<small class="text-muted">-</small>'

        return JsonResponse({
            'success': True,
            'message': f'{member.name} updated successfully',
            'member': {
                'id': member.id,
                'name': member.name,
                'paid_total': member.paid_total,
                'status': status,
                'status_html': status_html,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def add_member_ajaxs(request):
    """AJAX endpoint for adding new members"""
    try:
        data = json.loads(request.body)

        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'})

        # Check if member already exists
        if Member.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Member with this name already exists'})

        # Create new member
        member = Member(
            name=name,
            phone=data.get('phone_number', '').strip(),
            year=data.get('year_of_study', '').strip(),
        )

        # Set initial paid amount if user is staff
        if request.user.is_staff and 'paid_total' in data:
            try:
                paid_amount = float(data['paid_total'])
                if paid_amount < 0:
                    return JsonResponse({'success': False, 'error': 'Paid amount cannot be negative'})
                member.paid_total = paid_amount
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid paid amount'})

        member.save()

        return JsonResponse({
            'success': True,
            'message': f'{member.name} added successfully',
            'member': {
                'id': member.id,
                'name': member.name,
                'phone': member.phone,
                'year': member.year,
                'paid_total': member.paid_total,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_member_ajaxs(request):
    """AJAX endpoint for deleting members (staff only)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'})

    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')

        if not member_id:
            return JsonResponse({'success': False, 'error': 'Member ID is required'})

        try:
            member = Member.objects.get(id=member_id)
            member_name = member.name
            member.delete()

            return JsonResponse({
                'success': True,
                'message': f'{member_name} deleted successfully'
            })

        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Member not found'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})


# Helper function to validate and format phone numbers
def format_phone_number(phone_number):
    """Format phone number to international format"""
    if not phone_number:
        return None

    phone_number = phone_number.strip()

    # Remove spaces and hyphens
    phone_number = phone_number.replace(' ', '').replace('-', '')

    # Format to Tanzania international format
    if not phone_number.startswith('+'):
        if phone_number.startswith('0'):
            phone_number = '+255' + phone_number[1:]
        elif phone_number.startswith('255'):
            phone_number = '+' + phone_number
        elif phone_number.isdigit() and len(phone_number) >= 9:
            phone_number = '+255' + phone_number

    return phone_number


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def toggle_member_status_ajax(request):
    """AJAX view to toggle member active status"""
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')

        if not member_id:
            return JsonResponse({
                'success': False,
                'error': 'Member ID is required'
            })

        member = get_object_or_404(Member, id=member_id)

        # Toggle active status
        member.is_active = not member.is_active
        member.save()

        status = "activated" if member.is_active else "deactivated"

        return JsonResponse({
            'success': True,
            'message': f'Member {member.name} has been {status}',
            'is_active': member.is_active
        })

    except Member.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Member not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })

@login_required
def export_excel(request):
    """Export all members data to Excel with styling"""
    try:
        # Get all members with the same filtering logic as dashboard
        search_query = request.GET.get('search', '')
        filter_status = request.GET.get('filter', '')

        # Get members (using same logic as dashboard)
        members = []
        try:
            all_members = Member.objects.all()
            for member in all_members:
                try:
                    if member.pledge is None or member.paid_total is None:
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                    members.append(member)
                except Exception:
                    continue
        except Exception:
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

        # Create workbook and worksheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Members Data"

        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        center_alignment = Alignment(horizontal='center', vertical='center')
        currency_alignment = Alignment(horizontal='right', vertical='center')

        # Headers
        headers = [
            'Name', 'Phone', 'Email', 'Course', 'Year',
            'Pledge Amount', 'Paid Amount', 'Balance', 'Status', 'Progress %'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_alignment

        # Data rows
        for row_num, member in enumerate(members, 2):
            try:
                pledge = member.pledge if member.pledge is not None else Decimal('70000.00')
                paid = member.paid_total if member.paid_total is not None else Decimal('0.00')
                balance = pledge - paid
                progress = (paid / pledge * 100) if pledge > 0 else 0

                # Determine status
                if paid == 0:
                    status = "Not Started"
                elif paid < pledge:
                    status = "Incomplete"
                elif paid == pledge:
                    status = "Complete"
                else:
                    status = "Exceeded"

                # Data
                data = [
                    member.name,
                    member.phone or '',
                    member.email or '',
                    member.course or '',
                    member.year or '',
                    float(pledge),
                    float(paid),
                    float(balance),
                    status,
                    f"{progress:.1f}%"
                ]

                for col, value in enumerate(data, 1):
                    cell = ws.cell(row=row_num, column=col, value=value)
                    cell.border = border

                    # Special formatting for currency columns
                    if col in [6, 7, 8]:  # Pledge, Paid, Balance
                        cell.number_format = '#,##0.00'
                        cell.alignment = currency_alignment
                    else:
                        cell.alignment = center_alignment

            except Exception:
                continue

        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Add summary sheet
        summary_ws = wb.create_sheet("Summary")

        # Calculate totals
        total_members = len(members)
        total_pledged = sum(member.pledge or Decimal('70000.00') for member in members)
        total_collected = sum(member.paid_total or Decimal('0.00') for member in members)
        target_amount = Decimal('11000000.00')
        progress_percentage = (total_collected / target_amount * 100) if target_amount > 0 else 0

        # Summary data
        summary_data = [
            ['FUNDRAISING SUMMARY', ''],
            ['', ''],
            ['Total Members', total_members],
            ['Total Pledged', f"TSh {total_pledged:,.2f}"],
            ['Total Collected', f"TSh {total_collected:,.2f}"],
            ['Target Amount', f"TSh {target_amount:,.2f}"],
            ['Progress', f"{progress_percentage:.1f}%"],
            ['', ''],
            ['Export Date', date.today().strftime('%Y-%m-%d')],
        ]

        for row_num, (label, value) in enumerate(summary_data, 1):
            summary_ws.cell(row=row_num, column=1, value=label).font = Font(bold=True)
            summary_ws.cell(row=row_num, column=2, value=value)

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"members_data_{date.today().strftime('%Y%m%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Error exporting Excel: {str(e)}")
        return redirect('tracker:dashboard')
@login_required
def export_pdf(request):
    """Export all members data to PDF with styling, logo, and dynamic headings"""
    try:
        # Get all members with the same filtering logic as dashboard
        search_query = request.GET.get('search', '')
        filter_status = request.GET.get('filter', '')

        # Get members (using same logic as dashboard)
        members = []
        try:
            all_members = Member.objects.all()
            for member in all_members:
                try:
                    if member.pledge is None or member.paid_total is None:
                        if member.pledge is None:
                            member.pledge = Decimal('70000.00')
                        if member.paid_total is None:
                            member.paid_total = Decimal('0.00')
                        member.save()
                    members.append(member)
                except Exception:
                    continue
        except Exception:
            members = []

        # Apply same filters as Excel export
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

        # Create PDF with custom page template for logo
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=120, bottomMargin=60)

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#2c3e50')
        )

        filter_style = ParagraphStyle(
            'FilterStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#7f8c8d')
        )

        # Link style for download hyperlink
        link_style = ParagraphStyle(
            'LinkStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=15,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#3498db')
        )

        # Dynamic title based on filters
        base_title = "MEMBERS REPORT:MLALI MISSION"

        # Add filter information to title
        filter_info = []
        if filter_status:
            filter_map = {
                'incomplete': 'INCOMPLETE PAYMENTS',
                'complete': 'COMPLETE PAYMENTS',
                'pledged': 'PLEDGED ABOVE Tsh 70,000',
                'not_started': 'NOT STARTED',
                'exceeded': 'EXCEEDED PLEDGES'
            }
            filter_info.append(filter_map.get(filter_status, filter_status.upper()))

        if search_query:
            filter_info.append(f'SEARCH: "{search_query.upper()}"')

        if filter_info:
            title_text = f"{base_title}<br/><font size='14' color='#e74c3c'>({' - '.join(filter_info)})</font>"
        else:
            title_text = base_title

        # Title
        title = Paragraph(title_text, title_style)
        elements.append(title)

        # Add download link for latest version
        current_url = request.build_absolute_uri()
        download_link_text = f'<a href="{current_url}" color="#3498db"><u>Click here to download the latest version of this report</u></a>'
        download_link = Paragraph(download_link_text, link_style)
        elements.append(download_link)
        elements.append(Spacer(1, 12))

        # Summary section
        total_members = len(members)
        total_pledged = sum(member.pledge or Decimal('70000.00') for member in members)
        total_collected = sum(member.paid_total or Decimal('0.00') for member in members)
        target_amount = Decimal('11000000.00')
        progress_percentage = (total_collected / target_amount * 100) if target_amount > 0 else 0

        summary_data = [
            ['SUMMARY', ''],
            ['Total Members:', f"{total_members:,}"],
            ['Total Pledged:', f"TSh {total_pledged:,.2f}"],
            ['Total Collected:', f"TSh {total_collected:,.2f}"],
            ['Target Amount:', f"TSh {target_amount:,.2f}"],
            ['% Collected:', f"{progress_percentage:.1f}%"],
            ['Report Date:', date.today().strftime('%B %d, %Y')],
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Members table
        if members:
            # Table headers with index number
            headers = ['#', 'Name', 'Phone', 'Pledge', 'Paid', 'Exceed/Remain(-)', 'Status']

            # Prepare data
            table_data = [headers]

            for index, member in enumerate(members, 1):
                try:
                    pledge = member.pledge if member.pledge is not None else Decimal('70000.00')
                    paid = member.paid_total if member.paid_total is not None else Decimal('0.00')
                    balance = paid - pledge

                    if paid == 0:
                        status = "Not Started"
                    elif paid < pledge:
                        status = "Incomplete"
                    elif paid == pledge:
                        status = "Complete"
                    else:
                        status = "Exceeded"

                    row = [
                        str(index),  # Index number
                        member.name[:20] + "..." if len(member.name) > 20 else member.name,
                        member.phone[:15] if member.phone else '',
                        f"TSh {pledge:,.0f}",
                        f"TSh {paid:,.0f}",
                        f"TSh {balance:,.0f}",
                        status
                    ]
                    table_data.append(row)
                except Exception:
                    continue

            # Create table with adjusted column widths to accommodate index
            table = Table(table_data, colWidths=[0.4*inch, 1.3*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),

                # Data styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),

                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),

                # Currency column alignment
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
                # Index column alignment
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ]))

            # With this:
            if len(table_data) > 1:  # Only if there's data beyond headers
                # For very large tables, you might want to split them
                if len(table_data) > 36:  # Adjust this number based on your needs
                    # Split large tables into chunks
                    chunk_size = 200
                    for i in range(0, len(table_data), chunk_size):
                        if i == 0:
                            chunk_data = table_data[0:chunk_size+1]  # Include header
                        else:
                            chunk_data = [table_data[0]] + table_data[i:i+chunk_size]  # Header + data

                        chunk_table = Table(chunk_data, colWidths=[0.4*inch, 1.3*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
                        chunk_table.setStyle(TableStyle([
                            # Header styling
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
                            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                        ]))

                        elements.append(chunk_table)
                        if i + chunk_size < len(table_data) - 1:  # Not the last chunk
                            elements.append(PageBreak())
                else:
                    # For smaller tables, just add normally
                    elements.append(table)

# Custom page template with logo
        def add_logo_and_header(canvas, doc):
            """Add logo and header to each page"""
            canvas.saveState()

            # Set white background for entire page
            canvas.setFillColor(colors.white)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

            # Add logo (if exists)
            logo_path = None
            # Try different common logo locations
            logo_locations = [
                'static/images/logo.png',
                'static/images/logo.jpg',
                'static/img/logo.png',
                'static/img/logo.jpg',
                'staticfiles/images/logo.png',
                'staticfiles/images/logo.jpg',
                'media/logo.png',
                'media/logo.jpg',
                'logo.png',
                'logo.jpg'
            ]

            for path in logo_locations:
                try:
                    from django.conf import settings
                    import os
                    full_path = os.path.join(settings.BASE_DIR, path)
                    if os.path.exists(full_path):
                        logo_path = full_path
                        break
                except:
                    continue

            if logo_path:
                try:
                    from reportlab.lib.utils import ImageReader
                    from PIL import Image

                    # Open image with PIL to handle transparency
                    pil_image = Image.open(logo_path)

                    # Convert to RGB if it has transparency (RGBA) or is in other modes
                    if pil_image.mode in ('RGBA', 'LA', 'P'):
                        # Create white background
                        background = Image.new('RGB', pil_image.size, (255, 255, 255))
                        if pil_image.mode == 'P':
                            pil_image = pil_image.convert('RGBA')
                        background.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode in ('RGBA', 'LA') else None)
                        pil_image = background
                    elif pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')

                    logo = ImageReader(pil_image)
                    # Get original dimensions
                    logo_width, logo_height = pil_image.size

                    # Calculate scaled dimensions (max 100x50)
                    max_width, max_height = 100, 50
                    if logo_width > max_width or logo_height > max_height:
                        ratio = min(max_width/logo_width, max_height/logo_height)
                        logo_width *= ratio
                        logo_height *= ratio

                    # Position logo at top center
                    x = (A4[0] - logo_width) / 2  # Center horizontally
                    y = A4[1] - 80  # 80 points from top

                    # Draw the logo
                    canvas.drawImage(logo, x, y, width=logo_width, height=logo_height)
                except Exception as e:
                    # If logo fails, add text header instead
                    canvas.setFont('Helvetica-Bold', 14)
                    canvas.setFillColor(colors.HexColor('#2c3e50'))
                    canvas.drawCentredText(A4[0]/2, A4[1] - 50, "FUNDRAISING REPORT")
            else:
                # No logo found, add text header
                canvas.setFont('Helvetica-Bold', 14)
                canvas.setFillColor(colors.HexColor('#2c3e50'))
                canvas.drawCentredText(A4[0]/2, A4[1] - 50, "FUNDRAISING REPORT")

            # Add page number
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.black)
            canvas.drawRightString(A4[0] - 72, 30, f"Page {doc.page}")

            # Add generation date
            canvas.drawString(72, 30, f"Generated: {date.today().strftime('%B %d, %Y')}")

            canvas.restoreState()


        # Build PDF with custom page template
        doc.build(elements, onFirstPage=add_logo_and_header, onLaterPages=add_logo_and_header)

        # Create response
        pdf_data = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_data, content_type='application/pdf')

        # Dynamic filename based on filters
        filename_parts = ['members_report']
        if filter_status:
            filename_parts.append(filter_status)
        if search_query:
            filename_parts.append(f'search_{search_query.replace(" ", "_")}')
        filename_parts.append(date.today().strftime('%Y%m%d'))

        filename = f"{'_'.join(filename_parts)}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(request, f"Error exporting PDF: {str(e)}")
        return redirect('tracker:dashboard')
@csrf_exempt
@require_http_methods(["POST"])
@login_required
def update_transaction_ajax(request):
    """Update transaction amount and/or note via AJAX"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        new_amount = data.get('amount')
        new_note = data.get('note', '')

        # Get the transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)

        # Store old amount for recalculation
        old_amount = transaction.amount

        # Validate and update amount if provided
        if new_amount is not None:
            try:
                new_amount = Decimal(str(new_amount))

                # Validate amount
                if new_amount <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Amount must be greater than zero.'
                    })

                if new_amount > 10000000:  # 10 million TZS limit
                    return JsonResponse({
                        'success': False,
                        'error': 'Amount cannot exceed 10,000,000 TZS.'
                    })

                transaction.amount = new_amount

            except (InvalidOperation, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid amount format.'
                })

        # Update note
        if len(new_note.strip()) > 500:
            return JsonResponse({
                'success': False,
                'error': 'Note cannot exceed 500 characters.'
            })

        transaction.note = new_note.strip()
        transaction.save()

        # Recalculate member totals if amount changed
        if new_amount is not None and old_amount != new_amount:
            member = transaction.member
            # Recalculate paid_total from all transactions
            total_paid = member.transaction_set.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            member.paid_total = total_paid
            member.save()

        return JsonResponse({
            'success': True,
            'new_amount': float(transaction.amount),
            'new_note': transaction.note,
            'formatted_amount': f"TZS {transaction.amount:,.0f}"
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while updating the transaction.'
        })

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_transaction_ajax(request):
    """Delete transaction via AJAX"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')

        # Get the transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)
        member = transaction.member

        # Delete the transaction
        transaction.delete()

        # Recalculate member totals
        total_paid = member.transaction_set.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        member.paid_total = total_paid
        member.save()

        return JsonResponse({
            'success': True,
            'message': 'Transaction deleted successfully.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while deleting the transaction.'
        })

# Your updated member_detail view
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
            'can_edit': request.user.is_staff,  # Simple check
        }
        return render(request, 'tracker/member_detail.html', context)

    except Exception as e:
        messages.error(request, f'Error loading member details: {str(e)}')
        return redirect('tracker:dashboard')
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

    except Exception as e:
        # If everything fails, use default values
        pass

    context = {
        'members': members,
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
        'can_edit': request.user.is_staff,  # Simple check
    }

    return render(request, 'tracker/dashboard.html', context)

# Updated views.py - Add these new AJAX views and update your member_detail view


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

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def update_transaction_ajax(request):
    """Update transaction amount and/or note via AJAX"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        new_amount = data.get('amount')
        new_note = data.get('note', '')

        # Get the transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)

        # Store old amount for recalculation
        old_amount = transaction.amount

        # Validate and update amount if provided
        if new_amount is not None:
            try:
                new_amount = Decimal(str(new_amount))

                # Validate amount
                if new_amount <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Amount must be greater than zero.'
                    })

                if new_amount > 10000000:  # 10 million TZS limit
                    return JsonResponse({
                        'success': False,
                        'error': 'Amount cannot exceed 10,000,000 TZS.'
                    })

                transaction.amount = new_amount

            except (InvalidOperation, ValueError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid amount format.'
                })

        # Update note
        if len(new_note.strip()) > 500:
            return JsonResponse({
                'success': False,
                'error': 'Note cannot exceed 500 characters.'
            })

        transaction.note = new_note.strip()
        transaction.save()

        # Recalculate member totals if amount changed
        if new_amount is not None and old_amount != new_amount:
            member = transaction.member
            # You might want to add a method to recalculate totals
            # member.recalculate_totals()

        return JsonResponse({
            'success': True,
            'new_amount': float(transaction.amount),
            'new_note': transaction.note,
            'formatted_amount': f"TZS {transaction.amount:,.0f}"
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while updating the transaction.'
        })

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_transaction_ajax(request):
    """Delete transaction via AJAX"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')

        # Get the transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)
        member = transaction.member

        # Delete the transaction
        transaction.delete()

        # Recalculate member totals
        # member.recalculate_totals()

        return JsonResponse({
            'success': True,
            'message': 'Transaction deleted successfully.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while deleting the transaction.'
        })

# Update your existing edit_member view to include the transaction form
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

from django.contrib import messages
from decimal import Decimal, InvalidOperation
from io import BytesIO
import openpyxl
from datetime import date
from .models import Member, Transaction
from .forms import ExcelImportForm

@login_required
def import_excel(request):
    """Import members and payment transactions from an Excel file."""
    if request.method == 'POST':
        form = ExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = form.cleaned_data['excel_file']
            update_existing = form.cleaned_data['update_existing']
            default_pledge = form.cleaned_data['default_pledge']

            try:
                workbook = openpyxl.load_workbook(BytesIO(excel_file.read()))
                sheet = workbook.active

                created_count = 0
                updated_count = 0
                transaction_count = 0
                errors = []

                for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    try:
                        if not row[0]:
                            continue  # Skip rows without a name

                        name = str(row[0]).strip()
                        pledge = row[1]
                        paid = row[2] if len(row) > 2 else None
                        phone = str(row[3]).strip() if len(row) > 3 and row[3] else ''
                        email = str(row[4]).strip() if len(row) > 4 and row[4] else ''
                        course = str(row[5]).strip() if len(row) > 5 and row[5] else ''
                        year = str(row[6]).strip() if len(row) > 6 and row[6] else ''

                        # Pledge
                        try:
                            pledge = Decimal(str(pledge)) if pledge else default_pledge
                        except InvalidOperation:
                            pledge = default_pledge
                            errors.append(f"Row {idx}: Invalid pledge, using default for '{name}'")

                        # Paid
                        try:
                            paid = Decimal(str(paid)) if paid else Decimal('0.00')
                        except InvalidOperation:
                            paid = Decimal('0.00')
                            errors.append(f"Row {idx}: Invalid paid value for '{name}', using 0.00")

                        member_created = False
                        if update_existing:
                            member, member_created = Member.objects.update_or_create(
                                name=name,
                                defaults={
                                    'pledge': pledge,
                                    'phone': phone or None,
                                    'email': email or None,
                                    'course': course or None,
                                    'year': year or None,
                                }
                            )
                        else:
                            member = Member.objects.filter(name=name).first()
                            if not member:
                                member = Member.objects.create(
                                    name=name,
                                    pledge=pledge,
                                    phone=phone or None,
                                    email=email or None,
                                    course=course or None,
                                    year=year or None,
                                )
                                member_created = True
                            else:
                                errors.append(f"Row {idx}: Member '{name}' already exists and update is off.")
                                continue

                        if member_created:
                            created_count += 1
                        else:
                            updated_count += 1

                        # Transaction
                        if paid > 0:
                            existing_txn = Transaction.objects.filter(
                                member=member,
                                date=date.today(),
                                added_by=request.user,
                                note__icontains="Imported via Excel"
                            ).first()

                            if existing_txn:
                                # Update the amount if different
                                if existing_txn.amount != paid:
                                    existing_txn.amount = paid
                                    existing_txn.note = f"Updated via Excel on {date.today().isoformat()}"
                                    existing_txn.save()
                                    transaction_count += 1
                            else:
                                # Create new transaction
                                Transaction.objects.create(
                                    member=member,
                                    amount=paid,
                                    date=date.today(),
                                    added_by=request.user,
                                    note=f"Imported via Excel on {date.today().isoformat()}"
                                )
                                transaction_count += 1


                    except Exception as e:
                        errors.append(f"Row {idx}: Error processing member '{row[0]}' - {str(e)}")

                if created_count:
                    messages.success(request, f"✅ Created {created_count} new members.")
                if updated_count:
                    messages.info(request, f"🔄 Updated {updated_count} existing members.")
                if transaction_count:
                    messages.success(request, f"💰 Recorded {transaction_count} payments.")

                if errors:
                    for err in errors[:5]:
                        messages.warning(request, f"⚠️ {err}")
                    if len(errors) > 5:
                        messages.warning(request, f"...and {len(errors) - 5} more issues.")

                return redirect('tracker:dashboard')

            except Exception as e:
                messages.error(request, f"📄 Excel reading error: {str(e)}")

        else:
            messages.error(request, "⚠️ Invalid form submission.")
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
        'can_edit': request.user.is_staff,  # Simple check
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



@staff_member_required
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
        'can_edit': request.user.is_staff,  # Simple check
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



def offline_view(request):
    """Offline page for PWA"""
    return render(request, 'offline.html')
