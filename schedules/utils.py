# from collections import defaultdict
# import random
# from django.db import transaction
# from django.utils.timezone import now
# from django.db.models import Count, Sum

# from courses.models import Course
# from exams.models import Exam, StudentExam
# from enrollments.models import Enrollment
# from rooms.models import Room
# from  datetime import time, timedelta

# # Define the exam slots
# SLOTS = [
#     ('Morning', time(8, 0), time(11, 0)),
#     ('Afternoon', time(13, 0), time(16, 0)),
#     ('Evening', time(17, 0), time(20, 0)),
# ]
# FRIDAY_SLOTS = [SLOTS[0]]  # Only morning slot for Friday
# NO_EXAM_DAYS = ['Saturday']  # No exams on Saturday

# def get_exam_slots(start_date, max_slots=None):
#     """
#     Generate a list of available exam slots starting from a given date.
#     Each slot is a tuple of (date, label, start_time, end_time)
#     """
#     date_slots = []
#     current_date = start_date

#     while max_slots is None or len(date_slots) < max_slots:
#         weekday = current_date.strftime('%A')
#         if weekday not in NO_EXAM_DAYS:
#             slots = FRIDAY_SLOTS if weekday == 'Friday' else SLOTS
#             for label, start, end in slots:
#                 date_slots.append((current_date, label, start, end))
#                 if max_slots and len(date_slots) >= max_slots:
#                     break
#         current_date += timedelta(days=1)

#     return date_slots

# def analyze_student_course_conflicts():
#     """
#     Analyze which courses have students in common to help with scheduling
#     Returns a dictionary where keys are course pairs and values are the count of students enrolled in both
#     """
#     conflict_matrix = defaultdict(int)
    
#     # Get all enrollments grouped by student
#     student_courses = defaultdict(list)
#     for enrollment in Enrollment.objects.all():
#         student_courses[enrollment.student_id].append(enrollment.course_id)
    
#     # Build conflict matrix
#     for student_id, courses in student_courses.items():
#         for i, course1 in enumerate(courses):
#             for course2 in courses[i+1:]:
#                 course_pair = tuple(sorted([course1, course2]))
#                 conflict_matrix[course_pair] += 1
    
#     return conflict_matrix

# def find_compatible_courses(course_conflict_matrix):
#     """
#     Group courses into compatible pairs (or single courses) that can be scheduled together
#     Compatible means they don't share students
#     """
#     all_courses = set()
#     for course1, course2 in course_conflict_matrix.keys():
#         all_courses.add(course1)
#         all_courses.add(course2)
    
#     # Add any courses that don't appear in the conflict matrix
#     for course in Course.objects.values_list('id', flat=True):
#         all_courses.add(course)
    
#     # Build adjacency list for course compatibility graph
#     # Two courses are compatible if they don't share any students
#     compatibility_graph = {course: set() for course in all_courses}
#     for course1 in all_courses:
#         for course2 in all_courses:
#             if course1 != course2:
#                 pair = tuple(sorted([course1, course2]))
#                 if pair not in course_conflict_matrix or course_conflict_matrix[pair] == 0:
#                     compatibility_graph[course1].add(course2)
    
#     # Group compatible courses using a greedy algorithm
#     remaining_courses = set(all_courses)
#     grouped_pairs = []
    
#     while remaining_courses:
#         # Pick a course with the fewest compatible options
#         course1 = min(
#             [c for c in remaining_courses],
#             key=lambda c: len([rc for rc in compatibility_graph[c] if rc in remaining_courses]) \
#                 if len([rc for rc in compatibility_graph[c] if rc in remaining_courses]) > 0 \
#                 else float('inf')
#         )
        
#         remaining_courses.remove(course1)
#         course_group = [course1]
        
#         # Try to find a compatible course
#         compatible_options = [c for c in compatibility_graph[course1] if c in remaining_courses]
#         if compatible_options:
#             course2 = compatible_options[0]
#             course_group.append(course2)
#             remaining_courses.remove(course2)
        
#         grouped_pairs.append(course_group)
    
#     return grouped_pairs

# def student_course_assignment(course_pairs):
#     """
#     For each student, determine which courses they're enrolled in from the given pairs
#     Returns a mapping of student_id -> list of (pair_index, course_id)
#     """
#     student_assignments = defaultdict(list)
    
#     for pair_index, pair in enumerate(course_pairs):
#         for course_id in pair:
#             enrollments = Enrollment.objects.filter(course_id=course_id)
#             for enrollment in enrollments:
#                 student_assignments[enrollment.student_id].append((pair_index, course_id))
    
#     return student_assignments

# def detect_scheduling_conflicts(course_pairs, student_assignments, date_slots):
#     """
#     Detect potential scheduling conflicts for each pair and slot
#     Returns a conflict score for each combination of pair and slot
#     Lower scores are better (fewer conflicts)
#     """
#     num_pairs = len(course_pairs)
#     num_slots = len(date_slots)
    
#     # Initialize conflict matrix
#     conflict_scores = [[0 for _ in range(num_slots)] for _ in range(num_pairs)]
    
#     # Group slots by date
#     slots_by_date = defaultdict(list)
#     for slot_idx, (date, label, start, end) in enumerate(date_slots):
#         slots_by_date[date].append(slot_idx)
    
#     # Calculate conflicts
#     for student_id, assignments in student_assignments.items():
#         # Check if student has multiple exams on the same day
#         for pair_indices, course_ids in assignments:
#             for pair_idx1, _ in assignments:
#                 if pair_idx1 != pair_indices:
#                     # These two course pairs can't be scheduled on the same day
#                     for date, slot_indices in slots_by_date.items():
#                         for slot_idx1 in slot_indices:
#                             for slot_idx2 in slot_indices:
#                                 conflict_scores[pair_idx1][slot_idx1] += 1
#                                 conflict_scores[pair_indices][slot_idx2] += 1
    
#     return conflict_scores

# def calculate_room_requirements(course_pairs):
#     """
#     Calculate how many students need to be accommodated for each course pair
#     Returns a list of dictionaries with course_id -> student_count
#     """
#     room_requirements = []
    
#     for pair in course_pairs:
#         pair_requirements = {}
#         for course_id in pair:
#             student_count = Enrollment.objects.filter(course_id=course_id).count()
#             pair_requirements[course_id] = student_count
#         room_requirements.append(pair_requirements)
    
#     return room_requirements

# def get_total_room_capacity():
#     """Get the total capacity of all available rooms"""
#     return Room.objects.aggregate(total_capacity=Sum('capacity'))['total_capacity'] or 0

# def generate_exam_schedule(start_date=None, course_ids=None):
#     """
#     Generate an exam schedule that minimizes conflicts
#     Returns a list of created exams and any unaccommodated students
#     """
#     if not start_date:
#         start_date = now().date() + timedelta(days=1)
    
#     # Build conflict matrix
#     conflict_matrix = analyze_student_course_conflicts()
    
#     # Group courses into compatible pairs
#     course_pairs = find_compatible_courses(conflict_matrix)
    
#     # Filter course pairs if specific course_ids were requested
#     if course_ids:
#         course_ids_set = set(course_ids)
#         filtered_pairs = []
#         for pair in course_pairs:
#             filtered_pair = [c for c in pair if c in course_ids_set]
#             if filtered_pair:
#                 filtered_pairs.append(filtered_pair)
#         course_pairs = filtered_pairs
    
#     # Generate available exam slots
#     date_slots = get_exam_slots(start_date, max_slots=len(course_pairs) * 3)  # Ensure we have enough slots
    
#     # Determine student assignments and detect conflicts
#     student_assignments = student_course_assignment(course_pairs)
#     conflict_scores = detect_scheduling_conflicts(course_pairs, student_assignments, date_slots)
    
#     # Calculate room requirements
#     room_requirements = calculate_room_requirements(course_pairs)
#     total_room_capacity = get_total_room_capacity()
    
#     # Create a schedule using a greedy algorithm
#     exams_created = []
#     student_exam_dates = defaultdict(set)  # Track which dates each student has exams
#     unaccommodated_students = []
    
#     with transaction.atomic():
#         # Assign slots to course pairs in order of decreasing difficulty (highest conflict score)
#         pair_difficulties = [(i, max(conflict_scores[i])) for i in range(len(course_pairs))]
#         pair_difficulties.sort(key=lambda x: x[1], reverse=True)
        
#         assigned_slots = set()
        
#         for pair_idx, _ in pair_difficulties:
#             pair = course_pairs[pair_idx]
            
#             # Find the best slot for this pair (lowest conflict score)
#             best_slot_idx = None
#             best_slot_score = float('inf')
            
#             for slot_idx in range(len(date_slots)):
#                 if slot_idx in assigned_slots:
#                     continue
                
#                 slot_date, slot_label, _, _ = date_slots[slot_idx]
                
#                 # Check if any student already has an exam on this date
#                 has_conflict = False
#                 for course_id in pair:
#                     student_ids = Enrollment.objects.filter(course_id=course_id).values_list('student_id', flat=True)
#                     for student_id in student_ids:
#                         if slot_date in student_exam_dates[student_id]:
#                             has_conflict = True
#                             break
#                     if has_conflict:
#                         break
                
#                 if not has_conflict and conflict_scores[pair_idx][slot_idx] < best_slot_score:
#                     best_slot_idx = slot_idx
#                     best_slot_score = conflict_scores[pair_idx][slot_idx]
            
#             if best_slot_idx is None:
#                 raise ValueError("Cannot find suitable slot for all course pairs while maintaining schedule constraints.")
            
#             assigned_slots.add(best_slot_idx)
#             exam_date, label, start_time, end_time = date_slots[best_slot_idx]
            
#             # Create exams for each course in the pair
#             pair_exams = []
#             for course_id in pair:
#                 course = Course.objects.get(id=course_id)
                
#                 exam = Exam.objects.create(
#                     course=course,
#                     date=exam_date,
#                     start_time=start_time,
#                     end_time=end_time
#                 )
#                 exams_created.append(exam)
#                 pair_exams.append(exam)
                
#                 # Update student exam dates
#                 students = Enrollment.objects.filter(course=course)
#                 for enrollment in students:
#                     student_exam_dates[enrollment.student_id].add(exam_date)
            
#             # Allocate rooms for these exams
#             unaccommodated = allocate_shared_rooms(pair_exams)
#             unaccommodated_students.extend(unaccommodated)
    
#     return exams_created, unaccommodated_students

# def allocate_shared_rooms(exams):
#     """
#     Allocate students to shared rooms for the given exams
#     Each room should accommodate students from different exams
#     Returns a list of students who couldn't be accommodated
#     """
#     if not exams:
#         return []
        
#     if len(exams) == 1:
#         return allocate_single_exam_rooms(exams[0])
    
#     # Get rooms ordered by capacity
#     rooms = list(Room.objects.order_by('-capacity'))
    
#     if not rooms:
#         raise Exception("No rooms available for allocation.")
    
#     # Create student exam records and count students by course
#     student_exams_by_course = {}
#     students_count_by_course = {}
    
#     for exam in exams:
#         enrolled_students = Enrollment.objects.filter(course=exam.course).select_related('student')
        
#         student_exams = [
#             StudentExam(student=e.student, exam=exam) for e in enrolled_students
#         ]
#         StudentExam.objects.bulk_create(student_exams)
        
#         student_exam_qs = StudentExam.objects.filter(exam=exam).select_related('student')
#         student_exams_by_course[exam.id] = list(student_exam_qs)
#         students_count_by_course[exam.id] = len(student_exams_by_course[exam.id])
    
#     # Calculate total students and capacity
#     total_students = sum(students_count_by_course.values())
#     total_capacity = sum(r.capacity for r in rooms)
    
#     unaccommodated_students = []
    
#     # Handle case where we don't have enough room capacity
#     if total_students > total_capacity:
#         accommodated_count = total_capacity
        
#         # Distribute available capacity proportionally
#         accommodated_by_course = {}
#         for exam_id, count in students_count_by_course.items():
#             proportion = count / total_students
#             accommodated_by_course[exam_id] = int(proportion * accommodated_count)
        
#         # Distribute any remaining seats
#         total_accommodated = sum(accommodated_by_course.values())
#         if total_accommodated < accommodated_count:
#             remaining = accommodated_count - total_accommodated
#             for exam_id in sorted(students_count_by_course.keys()):
#                 if remaining <= 0:
#                     break
#                 accommodated_by_course[exam_id] += 1
#                 remaining -= 1
        
#         # Track unaccommodated students
#         for exam_id, student_exams in student_exams_by_course.items():
#             accommodated = accommodated_by_course[exam_id]
#             if accommodated < len(student_exams):
#                 unaccommodated = student_exams[accommodated:]
#                 unaccommodated_students.extend([se.student for se in unaccommodated])
#                 student_exams_by_course[exam_id] = student_exams[:accommodated]
    
#     # Allocate students to rooms
#     remaining_by_course = {exam_id: student_exams.copy() 
#                            for exam_id, student_exams in student_exams_by_course.items()}
    
#     # Anti-cheating: Shuffle students to make it harder for friends to sit together
#     for exam_id in remaining_by_course:
#         random.shuffle(remaining_by_course[exam_id])
    
#     # Distribute students across rooms
#     for room in rooms:
#         students_per_course = {}
#         remaining_capacity = room.capacity
        
#         if len(exams) == 1:
#             # Single exam case - use entire room capacity
#             exam_id = exams[0].id
#             students_per_course[exam_id] = min(len(remaining_by_course[exam_id]), remaining_capacity)
#         else:
#             # Multiple exams - try to split room capacity evenly
#             half_capacity = room.capacity // len(exams)
            
#             # First pass: allocate half capacity to each exam
#             for exam_id, remaining in remaining_by_course.items():
#                 students_per_course[exam_id] = min(len(remaining), half_capacity)
#                 remaining_capacity -= students_per_course[exam_id]
            
#             # Second pass: distribute any remaining capacity
#             for exam_id, remaining in sorted(remaining_by_course.items(), 
#                                            key=lambda x: len(x[1]), reverse=True):
#                 if remaining_capacity > 0 and len(remaining) > students_per_course[exam_id]:
#                     additional = min(remaining_capacity, len(remaining) - students_per_course[exam_id])
#                     students_per_course[exam_id] += additional
#                     remaining_capacity -= additional
        
#         # Assign students to this room
#         for exam_id, count in students_per_course.items():
#             if count > 0:
#                 students_to_assign = remaining_by_course[exam_id][:count]
#                 for se in students_to_assign:
#                     se.room = room
#                     se.save(update_fields=['room'])
                
#                 remaining_by_course[exam_id] = remaining_by_course[exam_id][count:]
    
#     # Track any students who still couldn't be assigned to rooms
#     for exam_id, remaining in remaining_by_course.items():
#         if remaining:
#             unaccommodated_students.extend([se.student for se in remaining])
    
#     return unaccommodated_students

# def allocate_single_exam_rooms(exam):
#     """
#     Allocate students to rooms for a single exam
#     Returns a list of students who couldn't be accommodated
#     """
#     rooms = list(Room.objects.order_by('-capacity'))
    
#     if not rooms:
#         raise Exception("No rooms available for allocation.")
    
#     student_exam_qs = StudentExam.objects.filter(exam=exam).select_related('student')
#     unassigned = list(student_exam_qs)
    
#     # Shuffle students to prevent friends from sitting together
#     random.shuffle(unassigned)
    
#     total_students = len(unassigned)
#     available_capacity = sum(r.capacity for r in rooms)
#     unaccommodated_students = []
    
#     # Handle case where we don't have enough room capacity
#     if total_students > available_capacity:
#         accommodated_count = available_capacity
#         unaccommodated_students = [se.student for se in unassigned[accommodated_count:]]
#         unassigned = unassigned[:accommodated_count]
    
#     # Assign students to rooms
#     for room in rooms:
#         if not unassigned:
#             break
            
#         chunk = unassigned[:room.capacity]
#         for se in chunk:
#             se.room = room
#             se.save(update_fields=['room'])
            
#         unassigned = unassigned[room.capacity:]
    
#     return unaccommodated_students

# def cancel_exam(exam_id):
#     """
#     Cancel a scheduled exam
#     Returns True if successful
#     """
#     with transaction.atomic():
#         StudentExam.objects.filter(exam_id=exam_id).delete()
#         Exam.objects.filter(id=exam_id).delete()
    
#     return True

# def reschedule_exam(exam_id, new_date, new_start_time=None, new_end_time=None):
#     """
#     Reschedule an exam to a new date and/or time
#     Checks for conflicts with existing student exams
#     Returns the updated exam instance
#     """
#     with transaction.atomic():
#         exam = Exam.objects.get(id=exam_id)
        
#         # Validate day of week
#         weekday = new_date.strftime('%A')
#         if weekday in NO_EXAM_DAYS:
#             raise ValueError(f"Cannot schedule an exam on {weekday}.")
        
#         # Check student conflicts
#         enrolled_students = Enrollment.objects.filter(course=exam.course)
#         for enrollment in enrolled_students:
#             existing_exams = StudentExam.objects.filter(
#                 student=enrollment.student, 
#                 exam__date=new_date
#             ).exclude(exam_id=exam_id)
            
#             if existing_exams.exists():
#                 raise ValueError(
#                     f"Student {enrollment.student.reg_no} already has an exam "
#                     f"scheduled on {new_date}."
#                 )
        
#         # Update exam details
#         exam.date = new_date
#         if new_start_time:
#             exam.start_time = new_start_time
#         if new_end_time:
#             exam.end_time = new_end_time
            
#         exam.save()
    
#     return exam

# def get_unaccommodated_students():
#     """
#     Get a list of students who couldn't be accommodated in the exam schedule
#     """
#     # Students without a room assignment
#     unaccommodated = StudentExam.objects.filter(room__isnull=True).select_related('student', 'exam__course')
    
#     result = []
#     for student_exam in unaccommodated:
#         result.append({
#             'student': student_exam.student,
#             'course': student_exam.exam.course,
#             'exam_date': student_exam.exam.date,
#             'exam_slot': (student_exam.exam.start_time, student_exam.exam.end_time)
#         })
    
#     return result

# def find_optimal_exam_dates(start_date=None):
#     """
#     Find optimal dates for scheduling exams based on the course enrollment patterns
#     """
#     if not start_date:
#         start_date = now().date() + timedelta(days=1)
    
#     # Get course conflict matrix
#     conflict_matrix = analyze_student_course_conflicts()
    
#     # Find compatible course pairs
#     course_pairs = find_compatible_courses(conflict_matrix)
    
#     # Calculate the minimum number of days needed
#     min_days_needed = len(course_pairs) // 3  # 3 slots per day
#     if len(course_pairs) % 3 > 0:
#         min_days_needed += 1
    
#     # Generate enough slots
#     date_slots = get_exam_slots(start_date, max_slots=min_days_needed * 3 + 5)  # Add buffer
    
#     return {
#         'start_date': start_date,
#         'suggested_end_date': start_date + timedelta(days=min_days_needed + 2),  # Add buffer
#         'min_days_needed': min_days_needed,
#         'course_pairs': course_pairs,
#         'available_slots': date_slots[:min_days_needed * 3]
#     }

# def verify_exam_schedule():
#     """
#     Verify that the current exam schedule has no conflicts
#     Returns a list of any conflicts found
#     """
#     conflicts = []
    
#     # Check for students with multiple exams in one day
#     student_exams = defaultdict(list)
#     for student_exam in StudentExam.objects.select_related('student', 'exam'):
#         student_exams[student_exam.student.id].append(student_exam)
    
#     for student_id, exams in student_exams.items():
#         exams_by_date = defaultdict(list)
#         for exam in exams:
#             exams_by_date[exam.exam.date].append(exam)
        
#         for date, day_exams in exams_by_date.items():
#             if len(day_exams) > 1:
#                 conflicts.append({
#                     'type': 'multiple_exams_per_day',
#                     'student_id': student_id,
#                     'date': date,
#                     'exams': [e.exam.id for e in day_exams]
#                 })
    
#     # Check for room overallocation
#     exams_by_slot = defaultdict(list)
#     for exam in Exam.objects.all():
#         slot_key = (exam.date, exam.start_time, exam.end_time)
#         exams_by_slot[slot_key].append(exam)
    
#     for slot, slot_exams in exams_by_slot.items():
#         if len(slot_exams) < 2:
#             continue
            
#         room_student_counts = defaultdict(lambda: defaultdict(int))
        
#         for exam in slot_exams:
#             student_exams = StudentExam.objects.filter(exam=exam).select_related('room')
#             for se in student_exams:
#                 if se.room:
#                     room_student_counts[se.room.id][exam.id] += 1
        
#         for room_id, exam_counts in room_student_counts.items():
#             room = Room.objects.get(id=room_id)
#             total_students = sum(exam_counts.values())
            
#             if total_students > room.capacity:
#                 conflicts.append({
#                     'type': 'room_overallocation',
#                     'room_id': room_id,
#                     'capacity': room.capacity,
#                     'allocated': total_students,
#                     'slot': slot,
#                     'exams': list(exam_counts.keys())
#                 })
    
#     return conflicts





from datetime import datetime, timedelta, time
from collections import defaultdict
import random
from django.db import transaction
from django.utils.timezone import now
from django.db.models import Count, Sum

from courses.models import Course
from exams.models import Exam, StudentExam
from enrollments.models import Enrollment
from rooms.models import Room

# Define the exam slots
SLOTS = [
    ('Morning', time(8, 0), time(11, 0)),
    ('Afternoon', time(13, 0), time(16, 0)),
    ('Evening', time(17, 0), time(20, 0)),
]
FRIDAY_SLOTS = [SLOTS[0]]  # Only morning slot for Friday
NO_EXAM_DAYS = ['Saturday']  # No exams on Saturday

def get_exam_slots(start_date, max_slots=None):
    """
    Generate a list of available exam slots starting from a given date.
    Each slot is a tuple of (date, label, start_time, end_time)
    """
    date_slots = []
    current_date = start_date

    while max_slots is None or len(date_slots) < max_slots:
        weekday = current_date.strftime('%A')
        if weekday not in NO_EXAM_DAYS:
            slots = FRIDAY_SLOTS if weekday == 'Friday' else SLOTS
            for label, start, end in slots:
                date_slots.append((current_date, label, start, end))
                if max_slots and len(date_slots) >= max_slots:
                    break
        current_date += timedelta(days=1)

    return date_slots

def analyze_student_course_conflicts():
    """
    Analyze which courses have students in common to help with scheduling
    Returns a dictionary where keys are course pairs and values are the count of students enrolled in both
    """
    conflict_matrix = defaultdict(int)
    
    # Get all enrollments grouped by student
    student_courses = defaultdict(list)
    for enrollment in Enrollment.objects.all():
        student_courses[enrollment.student_id].append(enrollment.course_id)
    
    # Build conflict matrix
    for student_id, courses in student_courses.items():
        for i, course1 in enumerate(courses):
            for course2 in courses[i+1:]:
                course_pair = tuple(sorted([course1, course2]))
                conflict_matrix[course_pair] += 1
    
    return conflict_matrix

def find_compatible_courses(course_conflict_matrix):
    """
    Group courses into compatible groups that can be scheduled together
    Compatible means they don't share students
    This function can group more than 2 courses per slot if they don't create conflicts
    """
    all_courses = set()
    for course1, course2 in course_conflict_matrix.keys():
        all_courses.add(course1)
        all_courses.add(course2)
    
    # Add any courses that don't appear in the conflict matrix
    for course in Course.objects.values_list('id', flat=True):
        all_courses.add(course)
    
    # Build adjacency list for course compatibility graph
    # Two courses are compatible if they don't share any students
    compatibility_graph = {course: set() for course in all_courses}
    for course1 in all_courses:
        for course2 in all_courses:
            if course1 != course2:
                pair = tuple(sorted([course1, course2]))
                if pair not in course_conflict_matrix or course_conflict_matrix[pair] == 0:
                    compatibility_graph[course1].add(course2)
    
    # Group compatible courses using a greedy algorithm
    remaining_courses = set(all_courses)
    course_groups = []
    
    while remaining_courses:
        # Start a new group
        course_group = []
        
        # Pick a course with the fewest compatible options
        if remaining_courses:
            course1 = min(
                [c for c in remaining_courses],
                key=lambda c: len([rc for rc in compatibility_graph[c] if rc in remaining_courses]) \
                    if len([rc for rc in compatibility_graph[c] if rc in remaining_courses]) > 0 \
                    else float('inf')
            )
            
            course_group.append(course1)
            remaining_courses.remove(course1)
            
            # Keep track of courses that are compatible with ALL courses in our group
            compatible_with_group = set(compatibility_graph[course1]) & remaining_courses
            
            # Add more courses to the group if possible (greedy approach)
            while compatible_with_group and len(course_group) < 10:  # Limit to 10 courses per group for practical reasons
                # Select the course with fewest remaining compatible options (to save harder-to-place courses for later)
                next_course = min(
                    compatible_with_group,
                    key=lambda c: len([rc for rc in compatibility_graph[c] if rc in remaining_courses])
                )
                
                course_group.append(next_course)
                remaining_courses.remove(next_course)
                
                # Update the set of courses compatible with the entire group
                compatible_with_group &= set(compatibility_graph[next_course])
                compatible_with_group &= remaining_courses
        
        if course_group:
            course_groups.append(course_group)
    
    return course_groups

def student_course_assignment(course_pairs):
    """
    For each student, determine which courses they're enrolled in from the given pairs
    Returns a mapping of student_id -> list of (pair_index, course_id)
    """
    student_assignments = defaultdict(list)
    
    for pair_index, pair in enumerate(course_pairs):
        for course_id in pair:
            enrollments = Enrollment.objects.filter(course_id=course_id)
            for enrollment in enrollments:
                student_assignments[enrollment.student_id].append((pair_index, course_id))
    
    return student_assignments

def detect_scheduling_conflicts(course_pairs, student_assignments, date_slots):
    """
    Detect potential scheduling conflicts for each pair and slot
    Returns a conflict score for each combination of pair and slot
    Lower scores are better (fewer conflicts)
    """
    num_pairs = len(course_pairs)
    num_slots = len(date_slots)
    
    # Initialize conflict matrix
    conflict_scores = [[0 for _ in range(num_slots)] for _ in range(num_pairs)]
    
    # Group slots by date
    slots_by_date = defaultdict(list)
    for slot_idx, (date, label, start, end) in enumerate(date_slots):
        slots_by_date[date].append(slot_idx)
    
    # Calculate conflicts
    for student_id, assignments in student_assignments.items():
        # Check if student has multiple exams on the same day
        for pair_indices, course_ids in assignments:
            for pair_idx1, _ in assignments:
                if pair_idx1 != pair_indices:
                    # These two course pairs can't be scheduled on the same day
                    for date, slot_indices in slots_by_date.items():
                        for slot_idx1 in slot_indices:
                            for slot_idx2 in slot_indices:
                                conflict_scores[pair_idx1][slot_idx1] += 1
                                conflict_scores[pair_indices][slot_idx2] += 1
    
    return conflict_scores

def calculate_room_requirements(course_pairs):
    """
    Calculate how many students need to be accommodated for each course pair
    Returns a list of dictionaries with course_id -> student_count
    """
    room_requirements = []
    
    for pair in course_pairs:
        pair_requirements = {}
        for course_id in pair:
            student_count = Enrollment.objects.filter(course_id=course_id).count()
            pair_requirements[course_id] = student_count
        room_requirements.append(pair_requirements)
    
    return room_requirements

def get_total_room_capacity():
    """Get the total capacity of all available rooms"""
    return Room.objects.aggregate(total_capacity=Sum('capacity'))['total_capacity'] or 0

def generate_exam_schedule(start_date=None, course_ids=None, semester=None):
    """
    Generate an exam schedule that minimizes conflicts
    Returns a list of created exams and any unaccommodated students
    """
    if not start_date:
        start_date = now().date() + timedelta(days=1)
    
    # Build conflict matrix
    conflict_matrix = analyze_student_course_conflicts()
    
    # Group courses into compatible pairs
    course_pairs = find_compatible_courses(conflict_matrix)
    
    # Filter course pairs if specific course_ids were requested
    if course_ids:
        course_ids_set = set(course_ids)
        filtered_pairs = []
        for pair in course_pairs:
            filtered_pair = [c for c in pair if c in course_ids_set]
            if filtered_pair:
                filtered_pairs.append(filtered_pair)
        course_pairs = filtered_pairs
    
    # Generate available exam slots
    date_slots = get_exam_slots(start_date, max_slots=len(course_pairs) * 3)  # Ensure we have enough slots
    
    # Determine student assignments and detect conflicts
    student_assignments = student_course_assignment(course_pairs)
    conflict_scores = detect_scheduling_conflicts(course_pairs, student_assignments, date_slots)
    
    # Calculate room requirements
    room_requirements = calculate_room_requirements(course_pairs)
    total_room_capacity = get_total_room_capacity()
    
    # Create a schedule using a greedy algorithm
    exams_created = []
    student_exam_dates = defaultdict(set)  # Track which dates each student has exams
    unaccommodated_students = []
    
    with transaction.atomic():
        # Assign slots to course pairs in order of decreasing difficulty (highest conflict score)
        pair_difficulties = [(i, max(conflict_scores[i])) for i in range(len(course_pairs))]
        pair_difficulties.sort(key=lambda x: x[1], reverse=True)
        
        assigned_slots = set()
        
        for pair_idx, _ in pair_difficulties:
            pair = course_pairs[pair_idx]
            
            # Find the best slot for this pair (lowest conflict score)
            best_slot_idx = None
            best_slot_score = float('inf')
            
            for slot_idx in range(len(date_slots)):
                if slot_idx in assigned_slots:
                    continue
                
                slot_date, slot_label, _, _ = date_slots[slot_idx]
                
                # Check if any student already has an exam on this date
                has_conflict = False
                for course_id in pair:
                    student_ids = Enrollment.objects.filter(course_id=course_id).values_list('student_id', flat=True)
                    for student_id in student_ids:
                        if slot_date in student_exam_dates[student_id]:
                            has_conflict = True
                            break
                    if has_conflict:
                        break
                
                if not has_conflict and conflict_scores[pair_idx][slot_idx] < best_slot_score:
                    best_slot_idx = slot_idx
                    best_slot_score = conflict_scores[pair_idx][slot_idx]
            
            if best_slot_idx is None:
                raise ValueError("Cannot find suitable slot for all course pairs while maintaining schedule constraints.")
            
            assigned_slots.add(best_slot_idx)
            exam_date, label, start_time, end_time = date_slots[best_slot_idx]
            
            # Create exams for each course in the pair
            pair_exams = []
            for course_id in pair:
                course = Course.objects.get(id=course_id)
                
                exam = Exam.objects.create(
                    course=course,
                    date=exam_date,
                    start_time=start_time,
                    end_time=end_time
                )
                exams_created.append(exam)
                pair_exams.append(exam)
                
                # Update student exam dates
                students = Enrollment.objects.filter(course=course)
                for enrollment in students:
                    student_exam_dates[enrollment.student_id].add(exam_date)
            
            # Allocate rooms for these exams
            unaccommodated = allocate_shared_rooms(pair_exams)
            unaccommodated_students.extend(unaccommodated)
    
    return exams_created, unaccommodated_students

def allocate_shared_rooms(exams):
    """
    Allocate students to shared rooms for the given exams
    Each room should accommodate students from multiple exams
    Returns a list of students who couldn't be accommodated
    """
    if not exams:
        return []
        
    if len(exams) == 1:
        return allocate_single_exam_rooms(exams[0])
    
    # Get rooms ordered by capacity
    rooms = list(Room.objects.order_by('-capacity'))
    
    if not rooms:
        raise Exception("No rooms available for allocation.")
    
    # Create student exam records and count students by course
    student_exams_by_course = {}
    students_count_by_course = {}
    
    for exam in exams:
        enrolled_students = Enrollment.objects.filter(course=exam.course).select_related('student')
        
        student_exams = [
            StudentExam(student=e.student, exam=exam) for e in enrolled_students
        ]
        StudentExam.objects.bulk_create(student_exams)
        
        student_exam_qs = StudentExam.objects.filter(exam=exam).select_related('student')
        student_exams_by_course[exam.id] = list(student_exam_qs)
        students_count_by_course[exam.id] = len(student_exams_by_course[exam.id])
    
    # Calculate total students and capacity
    total_students = sum(students_count_by_course.values())
    total_capacity = sum(r.capacity for r in rooms)
    
    unaccommodated_students = []
    
    # Handle case where we don't have enough room capacity
    if total_students > total_capacity:
        accommodated_count = total_capacity
        
        # Distribute available capacity proportionally
        accommodated_by_course = {}
        for exam_id, count in students_count_by_course.items():
            proportion = count / total_students
            accommodated_by_course[exam_id] = int(proportion * accommodated_count)
        
        # Distribute any remaining seats
        total_accommodated = sum(accommodated_by_course.values())
        if total_accommodated < accommodated_count:
            remaining = accommodated_count - total_accommodated
            for exam_id in sorted(students_count_by_course.keys()):
                if remaining <= 0:
                    break
                accommodated_by_course[exam_id] += 1
                remaining -= 1
        
        # Track unaccommodated students
        for exam_id, student_exams in student_exams_by_course.items():
            accommodated = accommodated_by_course[exam_id]
            if accommodated < len(student_exams):
                unaccommodated = student_exams[accommodated:]
                unaccommodated_students.extend([se.student for se in unaccommodated])
                student_exams_by_course[exam_id] = student_exams[:accommodated]
    
    # Allocate students to rooms
    remaining_by_course = {exam_id: student_exams.copy() 
                           for exam_id, student_exams in student_exams_by_course.items()}
    
    # Anti-cheating: Shuffle students to make it harder for friends to sit together
    for exam_id in remaining_by_course:
        random.shuffle(remaining_by_course[exam_id])
    
    # Distribute students across rooms
    for room in rooms:
        students_per_course = {}
        remaining_capacity = room.capacity
        
        if len(exams) == 1:
            # Single exam case - use entire room capacity
            exam_id = exams[0].id
            students_per_course[exam_id] = min(len(remaining_by_course[exam_id]), remaining_capacity)
        else:
            # Multiple exams - try to allocate room capacity fairly
            # Calculate seats per exam course based on proportional allocation
            course_capacity = room.capacity // len(exams)
            if course_capacity == 0:  # Room too small to fit all exam types
                course_capacity = 1  # Minimum allocation
            
            # First pass: allocate capacity to each exam with minimum of course_capacity
            for exam_id, remaining in remaining_by_course.items():
                students_per_course[exam_id] = min(len(remaining), course_capacity)
                remaining_capacity -= students_per_course[exam_id]
            
            # Second pass: distribute any remaining capacity
            if remaining_capacity > 0:
                # Sort by most remaining students
                sorted_exams = sorted(
                    remaining_by_course.items(), 
                    key=lambda x: len(x[1]) - students_per_course[x[0]], 
                    reverse=True
                )
                
                for exam_id, remaining in sorted_exams:
                    if remaining_capacity <= 0:
                        break
                        
                    if len(remaining) > students_per_course[exam_id]:
                        additional = min(remaining_capacity, len(remaining) - students_per_course[exam_id])
                        students_per_course[exam_id] += additional
                        remaining_capacity -= additional
        
        # Assign students to this room
        for exam_id, count in students_per_course.items():
            if count > 0:
                students_to_assign = remaining_by_course[exam_id][:count]
                for se in students_to_assign:
                    se.room = room
                    se.save(update_fields=['room'])
                
                remaining_by_course[exam_id] = remaining_by_course[exam_id][count:]
    
    # Track any students who still couldn't be assigned to rooms
    for exam_id, remaining in remaining_by_course.items():
        if remaining:
            unaccommodated_students.extend([se.student for se in remaining])
    
    return unaccommodated_students

def allocate_single_exam_rooms(exam):
    """
    Allocate students to rooms for a single exam
    Returns a list of students who couldn't be accommodated
    """
    rooms = list(Room.objects.order_by('-capacity'))
    
    if not rooms:
        raise Exception("No rooms available for allocation.")
    
    student_exam_qs = StudentExam.objects.filter(exam=exam).select_related('student')
    unassigned = list(student_exam_qs)
    
    # Shuffle students to prevent friends from sitting together
    random.shuffle(unassigned)
    
    total_students = len(unassigned)
    available_capacity = sum(r.capacity for r in rooms)
    unaccommodated_students = []
    
    # Handle case where we don't have enough room capacity
    if total_students > available_capacity:
        accommodated_count = available_capacity
        unaccommodated_students = [se.student for se in unassigned[accommodated_count:]]
        unassigned = unassigned[:accommodated_count]
    
    # Assign students to rooms
    for room in rooms:
        if not unassigned:
            break
            
        chunk = unassigned[:room.capacity]
        for se in chunk:
            se.room = room
            se.save(update_fields=['room'])
            
        unassigned = unassigned[room.capacity:]
    
    return unaccommodated_students

def cancel_exam(exam_id):
    """
    Cancel a scheduled exam
    Returns True if successful
    """
    with transaction.atomic():
        StudentExam.objects.filter(exam_id=exam_id).delete()
        Exam.objects.filter(id=exam_id).delete()
    
    return True

def reschedule_exam(exam_id, new_date, new_start_time=None, new_end_time=None):
    """
    Reschedule an exam to a new date and/or time
    Checks for conflicts with existing student exams
    Returns the updated exam instance
    """
    with transaction.atomic():
        exam = Exam.objects.get(id=exam_id)
        
        # Validate day of week
        weekday = new_date.strftime('%A')
        if weekday in NO_EXAM_DAYS:
            raise ValueError(f"Cannot schedule an exam on {weekday}.")
        
        # Check student conflicts
        enrolled_students = Enrollment.objects.filter(course=exam.course)
        for enrollment in enrolled_students:
            existing_exams = StudentExam.objects.filter(
                student=enrollment.student, 
                exam__date=new_date
            ).exclude(exam_id=exam_id)
            
            if existing_exams.exists():
                raise ValueError(
                    f"Student {enrollment.student.reg_no} already has an exam "
                    f"scheduled on {new_date}."
                )
        
        # Update exam details
        exam.date = new_date
        if new_start_time:
            exam.start_time = new_start_time
        if new_end_time:
            exam.end_time = new_end_time
            
        exam.save()
    
    return exam

def get_unaccommodated_students():
    """
    Get a list of students who couldn't be accommodated in the exam schedule
    """
    # Students without a room assignment
    unaccommodated = StudentExam.objects.filter(room__isnull=True).select_related('student', 'exam__course')
    
    result = []
    for student_exam in unaccommodated:
        result.append({
            'student': student_exam.student,
            'course': student_exam.exam.course,
            'exam_date': student_exam.exam.date,
            'exam_slot': (student_exam.exam.start_time, student_exam.exam.end_time)
        })
    
    return result

def find_optimal_exam_dates(start_date=None):
    """
    Find optimal dates for scheduling exams based on the course enrollment patterns
    """
    if not start_date:
        start_date = now().date() + timedelta(days=1)
    
    # Get course conflict matrix
    conflict_matrix = analyze_student_course_conflicts()
    
    # Find compatible course pairs
    course_pairs = find_compatible_courses(conflict_matrix)
    
    # Calculate the minimum number of days needed
    min_days_needed = len(course_pairs) // 3  # 3 slots per day
    if len(course_pairs) % 3 > 0:
        min_days_needed += 1
    
    # Generate enough slots
    date_slots = get_exam_slots(start_date, max_slots=min_days_needed * 3 + 5)  # Add buffer
    
    return {
        'start_date': start_date,
        'suggested_end_date': start_date + timedelta(days=min_days_needed + 2),  # Add buffer
        'min_days_needed': min_days_needed,
        'course_pairs': course_pairs,
        'available_slots': date_slots[:min_days_needed * 3]
    }

def verify_exam_schedule():
    """
    Verify that the current exam schedule has no conflicts
    Returns a list of any conflicts found
    """
    conflicts = []
    
    # Check for students with multiple exams in one day
    student_exams = defaultdict(list)
    for student_exam in StudentExam.objects.select_related('student', 'exam'):
        student_exams[student_exam.student.id].append(student_exam)
    
    for student_id, exams in student_exams.items():
        exams_by_date = defaultdict(list)
        for exam in exams:
            exams_by_date[exam.exam.date].append(exam)
        
        for date, day_exams in exams_by_date.items():
            if len(day_exams) > 1:
                conflicts.append({
                    'type': 'multiple_exams_per_day',
                    'student_id': student_id,
                    'date': date,
                    'exams': [e.exam.id for e in day_exams]
                })
    
    # Check for room overallocation
    exams_by_slot = defaultdict(list)
    for exam in Exam.objects.all():
        slot_key = (exam.date, exam.start_time, exam.end_time)
        exams_by_slot[slot_key].append(exam)
    
    for slot, slot_exams in exams_by_slot.items():
        room_student_counts = defaultdict(lambda: defaultdict(int))
        
        for exam in slot_exams:
            student_exams = StudentExam.objects.filter(exam=exam).select_related('room')
            for se in student_exams:
                if se.room:
                    room_student_counts[se.room.id][exam.id] += 1
        
        for room_id, exam_counts in room_student_counts.items():
            room = Room.objects.get(id=room_id)
            total_students = sum(exam_counts.values())
            
            if total_students > room.capacity:
                conflicts.append({
                    'type': 'room_overallocation',
                    'room_id': room_id,
                    'capacity': room.capacity,
                    'allocated': total_students,
                    'slot': slot,
                    'exams': list(exam_counts.keys())
                })
    
    # Check for courses in same slot without being in same group
    # (they shouldn't share any students)
    exams_by_slot = defaultdict(list)
    for exam in Exam.objects.all():
        slot_key = (exam.date, exam.start_time, exam.end_time)
        exams_by_slot[slot_key].append(exam)
    
    for slot, slot_exams in exams_by_slot.items():
        # Skip slots with only one exam
        if len(slot_exams) < 2:
            continue
            
        # For each pair of exams in this slot, check if they share students
        for i, exam1 in enumerate(slot_exams):
            for exam2 in slot_exams[i+1:]:
                # Check if these exams share any students
                students1 = set(Enrollment.objects.filter(course=exam1.course).values_list('student_id', flat=True))
                students2 = set(Enrollment.objects.filter(course=exam2.course).values_list('student_id', flat=True))
                
                common_students = students1.intersection(students2)
                if common_students:
                    conflicts.append({
                        'type': 'student_exam_conflict',
                        'course1': exam1.course.id,
                        'course2': exam2.course.id,
                        'common_students': list(common_students),
                        'slot': slot
                    })
    
    return conflicts