/* Hospital Management System UI. All data is loaded from the Flask/Oracle API. */
'use strict';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'departments', label: 'Departments', icon: 'departments' },
  { id: 'doctors', label: 'Doctors', icon: 'doctors' },
  { id: 'patients', label: 'Patients', icon: 'patients' },
  { id: 'appointments', label: 'Appointments', icon: 'appointments' },
  { id: 'rooms', label: 'Rooms', icon: 'rooms' },
  { id: 'admissions', label: 'Admissions', icon: 'admissions' },
  { id: 'medicines', label: 'Medicines', icon: 'medicines' },
  { id: 'prescriptions', label: 'Prescriptions', icon: 'prescriptions' },
  { id: 'bills', label: 'Billing', icon: 'bills' },
  { id: 'reports', label: 'Reports', icon: 'reports' },
];

const ICON_PATHS = {
  dashboard: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
  departments: '<path d="M4 21h16M6 21V5l6-2 6 2v16M9 9h.01M15 9h.01M9 13h.01M15 13h.01M10 21v-4h4v4"/>',
  doctors: '<circle cx="12" cy="7" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2M19 5v5M16.5 7.5h5"/>',
  patients: '<circle cx="9" cy="8" r="3.25"/><path d="M2.5 20v-1.5a6.5 6.5 0 0 1 13 0V20M16 5.5a3.25 3.25 0 0 1 0 6.25M18 14a5 5 0 0 1 3.5 4.5V20"/>',
  appointments: '<rect x="3.5" y="5" width="17" height="16" rx="2"/><path d="M7.5 3v4M16.5 3v4M3.5 9.5h17M8 13h3M8 17h3M15 13h2"/>',
  rooms: '<path d="M3 5v16M21 12v9M3 17h18M6 13h5a4 4 0 0 1 4 4M7 9h4a2 2 0 0 1 2 2v2"/>',
  admissions: '<path d="M13 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5M3 12h12M11 8l4 4-4 4"/>',
  medicines: '<path d="M6.6 17.4a5 5 0 0 1 0-7.1l3.8-3.8a5 5 0 0 1 7.1 7.1l-3.8 3.8a5 5 0 0 1-7.1 0Z"/><path d="m9.2 8.2 6.6 6.6"/>',
  prescriptions: '<rect x="4" y="4" width="16" height="18" rx="2"/><path d="M9 4.5h6M8 10h8M8 14h8M8 18h5"/>',
  bills: '<path d="M5 3.5h14v17l-3-1.7-4 1.7-4-1.7-3 1.7zM9 8h6M9 12h6M9 16h3"/>',
  reports: '<path d="M3.5 20.5h17M5.5 18V11h4v7M10.5 18V5h4v13M15.5 18V8h4v10"/>',
};

function renderIcon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ICON_PATHS.dashboard}</svg>`;
}

const CHOICES = {
  gender: [{ value: 'M', label: 'Male' }, { value: 'F', label: 'Female' }, { value: 'O', label: 'Other' }],
  appointment_status: ['Scheduled', 'Checked In', 'Waiting', 'In Consultation', 'Completed', 'Cancelled', 'No-show'].map((value) => ({ value, label: value })),
  room_status: ['Available', 'Occupied', 'Maintenance'].map((value) => ({ value, label: value })),
  room_type: ['General', 'Semi-private', 'Private', 'ICU'].map((value) => ({ value, label: value })),
  ledger_status: ['Unpaid', 'Partial', 'Paid', 'Voided'].map((value) => ({ value, label: value })),
  payment_status: ['Unpaid', 'Partial', 'Paid'].map((value) => ({ value, label: value })),
  blood_group: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((value) => ({ value, label: value })),
  low_stock: [{ value: 'true', label: 'Low stock (< 10)' }, { value: 'false', label: 'In stock (10+)' }],
};

const MODULES = {
  departments: {
    title: 'Departments', description: 'Organize clinical services and see the doctors assigned to each department.',
    endpoint: 'departments', addLabel: 'Add department', singular: 'department',
    columns: [{ key: 'department_name', label: 'Department', sort: true, strong: true }, { key: 'location', label: 'Location' }, { key: 'associated_doctors', label: 'Associated doctors' }, { key: 'doctor_count', label: 'Count', align: 'right' }],
    fields: [
      { key: 'department_name', label: 'Department name', required: true, maxLength: 100, placeholder: 'e.g. Neurology' },
      { key: 'location', label: 'Location', required: true, maxLength: 150, placeholder: 'Building and floor' },
    ],
    filters: [],
  },
  doctors: {
    title: 'Doctors', description: 'Maintain clinician profiles, contact information, and department assignments.',
    endpoint: 'doctors', addLabel: 'Register doctor', singular: 'doctor',
    columns: [{ key: 'doctor_name', label: 'Doctor', strong: true, sort: true }, { key: 'specialization', label: 'Specialization', sort: true }, { key: 'department_name', label: 'Department', sort: true }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }],
    fields: [
      { key: 'doctor_name', label: 'Doctor name', required: true, maxLength: 150, placeholder: 'Dr. Firstname Lastname' },
      { key: 'specialization', label: 'Specialization', required: true, maxLength: 120, placeholder: 'Clinical specialty' },
      { key: 'department_id', label: 'Department', type: 'related', source: 'departments', required: true },
      { key: 'phone', label: 'Phone', type: 'tel', maxLength: 20, placeholder: '+91-90000-00000' },
      { key: 'email', label: 'Email', type: 'email', maxLength: 254, placeholder: 'doctor@example.test' },
    ],
    filters: [{ key: 'department_id', label: 'All departments', source: 'departments' }],
  },
  patients: {
    title: 'Patients', description: 'Search patient records and review linked clinical and billing history.',
    endpoint: 'patients', addLabel: 'Register patient', singular: 'patient',
    columns: [{ key: 'patient_name', label: 'Patient', strong: true, sort: true }, { key: 'date_of_birth', label: 'Date of birth', format: 'date', sort: true }, { key: 'gender', label: 'Gender', format: 'gender' }, { key: 'phone', label: 'Phone' }, { key: 'blood_group', label: 'Blood group' }],
    fields: [
      { key: 'patient_name', label: 'Patient name', required: true, maxLength: 150, placeholder: 'Full name' },
      { key: 'date_of_birth', label: 'Date of birth', type: 'date', required: true },
      { key: 'gender', label: 'Gender', type: 'select', choices: 'gender', required: true },
      { key: 'phone', label: 'Phone', type: 'tel', maxLength: 20, placeholder: '+91-90000-00000' },
      { key: 'blood_group', label: 'Blood group', type: 'select', choices: 'blood_group', optional: true, includeBlank: true },
      { key: 'address', label: 'Address', type: 'textarea', maxLength: 300, optional: true, full: true, placeholder: 'Street, locality, city' },
    ],
    filters: [
      { key: 'gender', label: 'All genders', choices: 'gender' },
      { key: 'blood_group', label: 'All blood groups', choices: 'blood_group' },
    ],
  },
  appointments: {
    title: 'Appointments', description: 'Book visits, manage the daily check-in queue, and preserve valid appointment history.',
    endpoint: 'appointments', addLabel: 'Book appointment', singular: 'appointment',
    columns: [{ key: 'appointment_date', label: 'Date', format: 'date', sort: true }, { key: 'appointment_time', label: 'Time', sort: true }, { key: 'duration_minutes', label: 'Minutes' }, { key: 'patient_name', label: 'Patient', strong: true, sort: true }, { key: 'doctor_name', label: 'Doctor', sort: true }, { key: 'department_name', label: 'Department' }, { key: 'status', label: 'Status', format: 'status', sort: true }],
    fields: [
      { key: 'patient_id', label: 'Patient', type: 'related', source: 'patients', required: true },
      { key: 'doctor_id', label: 'Doctor', type: 'related', source: 'doctors', required: true },
      { key: 'appointment_date', label: 'Appointment date', type: 'date', required: true },
      { key: 'appointment_time', label: 'Appointment time', type: 'time', required: true, hint: 'Use 24-hour time.' },
      { key: 'duration_minutes', label: 'Duration (minutes)', type: 'number', required: true, min: '1', step: '1', default: '30', hint: 'Visits must end by midnight. Active visits cannot overlap for a doctor.' },
    ],
    filters: [
      { key: 'patient_id', label: 'All patients', source: 'patients' },
      { key: 'doctor_id', label: 'All doctors', source: 'doctors' },
      { key: 'status', label: 'All statuses', choices: 'appointment_status' },
      { key: 'date_from', label: 'From date', type: 'date' },
      { key: 'date_to', label: 'To date', type: 'date' },
    ],
    noDelete: true,
  },
  rooms: {
    title: 'Rooms', description: 'Monitor room types and availability; active admissions manage Occupied status.',
    endpoint: 'rooms', addLabel: 'Add room', singular: 'room',
    columns: [{ key: 'room_number', label: 'Room', strong: true, sort: true }, { key: 'room_type', label: 'Type', sort: true }, { key: 'availability_status', label: 'Availability', format: 'status', sort: true }],
    fields: [
      { key: 'room_number', label: 'Room number', required: true, maxLength: 20, placeholder: 'e.g. R-201' },
      { key: 'room_type', label: 'Room type', type: 'select', choices: 'room_type', required: true },
      { key: 'availability_status', label: 'Availability', type: 'select', choices: 'room_status', required: true, default: 'Available', hint: 'Occupied status is changed by an active admission.' },
    ],
    filters: [{ key: 'availability_status', label: 'All availability', choices: 'room_status' }],
  },
  admissions: {
    title: 'Admissions', description: 'Admit patients to available rooms and discharge them to release rooms safely.',
    endpoint: 'admissions', addLabel: 'Admit patient', singular: 'admission',
    columns: [{ key: 'patient_name', label: 'Patient', strong: true }, { key: 'room_number', label: 'Room' }, { key: 'admission_date', label: 'Admitted', format: 'date', sort: true }, { key: 'discharge_date', label: 'Discharged', format: 'date' }, { key: 'admission_state', label: 'Status', format: 'admission' }],
    fields: [
      { key: 'patient_id', label: 'Patient', type: 'related', source: 'patients', required: true },
      { key: 'room_id', label: 'Available room', type: 'related', source: 'available_rooms', required: true, hint: 'Only currently available rooms are listed.' },
      { key: 'admission_date', label: 'Admission date', type: 'date', required: true },
    ],
    filters: [
      { key: 'active', label: 'All admissions', choices: [{ value: 'true', label: 'Active' }, { value: 'false', label: 'Discharged' }] },
      { key: 'patient_id', label: 'All patients', source: 'patients' },
      { key: 'room_id', label: 'All rooms', source: 'rooms' },
      { key: 'date_from', label: 'Admitted from', type: 'date' },
      { key: 'date_to', label: 'Admitted through', type: 'date' },
    ],
    noEdit: true,
    noDelete: true,
  },
  medicines: {
    title: 'Medicines', description: 'Maintain medicine catalogue, prices, and stock. Prescription entry does not dispense stock.',
    endpoint: 'medicines', addLabel: 'Add medicine', singular: 'medicine',
    columns: [{ key: 'medicine_name', label: 'Medicine', strong: true, sort: true }, { key: 'manufacturer', label: 'Manufacturer' }, { key: 'price', label: 'Price', format: 'money', sort: true }, { key: 'stock_quantity', label: 'In stock', format: 'stock', sort: true }],
    fields: [
      { key: 'medicine_name', label: 'Medicine name', required: true, maxLength: 150, placeholder: 'Name and strength' },
      { key: 'manufacturer', label: 'Manufacturer', maxLength: 150, optional: true },
      { key: 'price', label: 'Unit price (INR)', type: 'number', required: true, min: '0', step: '0.01', default: '0.00' },
      { key: 'stock_quantity', label: 'Stock quantity', type: 'number', required: true, min: '0', step: '1', default: '0' },
    ],
    filters: [{ key: 'low_stock', label: 'All stock levels', choices: 'low_stock' }],
  },
  prescriptions: {
    title: 'Prescriptions', description: 'Record medication instructions and view patient, clinician, and medicine history.',
    endpoint: 'prescriptions', addLabel: 'Create prescription', singular: 'prescription',
    columns: [{ key: 'prescription_date', label: 'Date', format: 'date', sort: true }, { key: 'patient_name', label: 'Patient', strong: true, sort: true }, { key: 'doctor_name', label: 'Doctor', sort: true }, { key: 'medicine_name', label: 'Medicine', sort: true }, { key: 'dosage', label: 'Dosage' }, { key: 'duration', label: 'Duration' }],
    fields: [
      { key: 'patient_id', label: 'Patient', type: 'related', source: 'patients', required: true },
      { key: 'doctor_id', label: 'Doctor', type: 'related', source: 'doctors', required: true },
      { key: 'medicine_id', label: 'Medicine', type: 'related', source: 'medicines', required: true },
      { key: 'dosage', label: 'Dosage', required: true, maxLength: 200, placeholder: 'e.g. 1 tablet after meals' },
      { key: 'duration', label: 'Duration', required: true, maxLength: 100, placeholder: 'e.g. 5 days' },
      { key: 'prescription_date', label: 'Prescription date', type: 'date', required: true },
    ],
    filters: [
      { key: 'patient_id', label: 'All patients', source: 'patients' },
      { key: 'doctor_id', label: 'All doctors', source: 'doctors' },
      { key: 'medicine_id', label: 'All medicines', source: 'medicines' },
      { key: 'date_from', label: 'From date', type: 'date' },
      { key: 'date_to', label: 'To date', type: 'date' },
    ],
    noDelete: true,
  },
  bills: {
    title: 'Billing', description: 'Invoice totals include additional items. Net collection and outstanding amounts include retained manager corrections.',
    endpoint: 'bills', addLabel: 'Create bill', singular: 'bill',
    columns: [{ key: 'bill_id', label: 'Bill', format: 'recordId' }, { key: 'patient_name', label: 'Patient', strong: true }, { key: 'bill_date', label: 'Bill date', format: 'date', sort: true }, { key: 'consultation_charge', label: 'Consultation', format: 'money' }, { key: 'room_charge', label: 'Room', format: 'money' }, { key: 'medicine_charge', label: 'Medicine', format: 'money' }, { key: 'total_amount', label: 'Invoice total', format: 'money', sort: true }, { key: 'payment_status', label: 'Ledger status', format: 'status', sort: true }, {key:'paid',label:'Net collected',format:'money'}, {key:'balance',label:'Outstanding',format:'money'}],
    fields: [
      { key: 'patient_id', label: 'Patient', type: 'related', source: 'patients', required: true },
      { key: 'bill_date', label: 'Bill date', type: 'date', required: true },
      { key: 'consultation_charge', label: 'Consultation charge (INR)', type: 'number', min: '0', step: '0.01', required: true, default: '0.00', hint: 'Enter the consultation/service fee.' },
      { key: 'room_charge', label: 'Room charge (INR)', type: 'number', min: '0', step: '0.01', required: true, default: '0.00', hint: 'Enter the agreed stay charge; no automatic per-night calculation is made.' },
      { key: 'medicine_charge', label: 'Medicine charge (INR)', type: 'number', min: '0', step: '0.01', required: true, default: '0.00', hint: 'Enter the billed medicine amount; prescriptions are not automatically dispensed.' },
      { key: 'notes', label: 'Administrative notes', type: 'text', maxLength: 300 },
    ],
    filters: [
      { key: 'patient_id', label: 'All patients', source: 'patients' },
      { key: 'payment_status', label: 'All payment statuses', choices: 'ledger_status' },
      { key: 'date_from', label: 'From date', type: 'date' },
      { key: 'date_to', label: 'To date', type: 'date' },
    ],
    noDelete: true,
  },
};

const REPORTS = {
  'department-doctor-counts': {
    title: 'Department-wise doctor counts',
    description: 'Doctors grouped by their assigned department (LEFT JOIN and GROUP BY).',
    filters: [],
    columns: [{ key: 'department_name', label: 'Department', strong: true }, { key: 'location', label: 'Location' }, { key: 'doctor_count', label: 'Doctor count' }],
  },
  'patient-appointments': {
    title: 'Patient appointment histories',
    description: 'Appointment records joined to their patient, doctor, and department.',
    filters: ['patient_id', 'doctor_id', 'status', 'date_from', 'date_to'],
    columns: [{ key: 'appointment_date', label: 'Date', format: 'date' }, { key: 'appointment_time', label: 'Time' }, { key: 'patient_name', label: 'Patient' }, { key: 'doctor_name', label: 'Doctor' }, { key: 'department_name', label: 'Department' }, { key: 'status', label: 'Status', format: 'status' }],
  },
  'doctor-schedule': {
    title: 'Upcoming doctor schedules',
    description: 'Scheduled and in-progress visits from today onwards, optionally filtered to one doctor.',
    filters: ['doctor_id', 'date_from', 'date_to'],
    columns: [{ key: 'appointment_date', label: 'Date', format: 'date' }, { key: 'appointment_time', label: 'Time' }, { key: 'doctor_name', label: 'Doctor' }, { key: 'patient_name', label: 'Patient' }, { key: 'department_name', label: 'Department' }, { key: 'status', label: 'Status', format: 'status' }],
  },
  'appointments-by-date-status': {
    title: 'Appointments by date and status',
    description: 'Daily appointment counts grouped by status.',
    filters: ['status', 'date_from', 'date_to'],
    columns: [{ key: 'appointment_date', label: 'Date', format: 'date' }, { key: 'status', label: 'Status', format: 'status' }, { key: 'appointment_count', label: 'Appointments' }],
  },
  'current-admissions': {
    title: 'Current admissions and room occupancy',
    description: 'Active patients and the rooms they currently occupy.',
    filters: ['patient_id', 'room_id', 'date_from', 'date_to'],
    columns: [{ key: 'patient_name', label: 'Patient' }, { key: 'room_number', label: 'Room' }, { key: 'room_type', label: 'Room type' }, { key: 'admission_date', label: 'Admitted', format: 'date' }],
  },
  'admission-history': {
    title: 'Admission and discharge history',
    description: 'Historical stays are retained after room release.',
    filters: ['patient_id', 'room_id', 'date_from', 'date_to'],
    columns: [{ key: 'patient_name', label: 'Patient' }, { key: 'room_number', label: 'Room' }, { key: 'admission_date', label: 'Admitted', format: 'date' }, { key: 'discharge_date', label: 'Discharged', format: 'date' }],
  },
  'room-assignment-history': {
    title: 'Room assignment history',
    description: 'Room changes recorded by this version. Legacy assignment start and end times may be unknown.',
    filters: ['patient_id', 'room_id'],
    columns: [{ key: 'patient_name', label: 'Patient' }, { key: 'admission_id', label: 'Admission', format: 'recordId' }, { key: 'room_number', label: 'Room' }, { key: 'started_at', label: 'Recorded start' }, { key: 'ended_at', label: 'Recorded end' }, { key: 'is_active', label: 'Active' }, { key: 'source', label: 'Source' }],
  },
  'room-occupancy': {
    title: 'Room availability summary',
    description: 'Room counts by current database availability status.',
    filters: [],
    columns: [{ key: 'availability_status', label: 'Status', format: 'status' }, { key: 'room_count', label: 'Rooms' }],
  },
  'low-stock-inventory': {
    title: 'Low-stock medicines',
    description: 'Medicine inventory below the project low-stock threshold of ten units.',
    filters: [],
    columns: [{ key: 'medicine_name', label: 'Medicine' }, { key: 'manufacturer', label: 'Manufacturer' }, { key: 'price', label: 'Unit price', format: 'money' }, { key: 'stock_quantity', label: 'Stock', format: 'stock' }],
  },
  'prescription-history': {
    title: 'Patient prescription histories',
    description: 'Prescriptions joined to the patient, clinician, and single linked medicine.',
    filters: ['patient_id', 'doctor_id', 'medicine_id', 'date_from', 'date_to'],
    columns: [{ key: 'prescription_date', label: 'Date', format: 'date' }, { key: 'patient_name', label: 'Patient' }, { key: 'doctor_name', label: 'Doctor' }, { key: 'medicine_name', label: 'Medicine' }, { key: 'dosage', label: 'Dosage' }, { key: 'duration', label: 'Duration' }],
  },
  'patient-bills': {
    title: 'Patient invoices and ledger status',
    description: 'Invoice totals include base categories and items; receipts minus refunds and retained charge corrections determine net status and balance.',
    filters: ['patient_id', 'payment_status', 'date_from', 'date_to'],
    columns: [{ key: 'bill_id', label: 'Bill', format: 'recordId' }, { key: 'bill_date', label: 'Date', format: 'date' }, { key: 'patient_name', label: 'Patient' }, { key: 'consultation_charge', label: 'Consultation', format: 'money' }, { key: 'room_charge', label: 'Room', format: 'money' }, { key: 'medicine_charge', label: 'Medicine', format: 'money' }, { key: 'total_amount', label: 'Total', format: 'money' }, { key: 'payment_status', label: 'Ledger status', format: 'status' },{key:'paid',label:'Net collected',format:'money'},{key:'balance',label:'Balance',format:'money'}],
  },
  'invoice-balances': {
    title: 'Invoice balances and payments',
    description: 'Legacy charge categories plus additional items, less recorded payments. Old Paid labels are not payments.',
    filters: ['patient_id', 'date_from', 'date_to'],
    columns: [{ key: 'bill_id', label: 'Bill', format: 'recordId' }, { key: 'patient_name', label: 'Patient' }, { key: 'bill_date', label: 'Date', format: 'date' }, { key: 'legacy_charges', label: 'Legacy charges', format: 'money' }, { key: 'billed', label: 'Billed', format: 'money' }, { key: 'paid', label: 'Net collected', format: 'money' }, { key: 'balance', label: 'Balance', format: 'money' }],
  },
  'billing-by-status': {
    title: 'Invoices by ledger status',
    description: 'Invoice counts, totals, recorded payments and balances grouped by derived ledger status.',
    filters: [],
    columns: [{ key: 'payment_status', label: 'Status', format: 'status' }, { key: 'bill_count', label: 'Bills' }, { key: 'total_amount', label: 'Total', format: 'money' },{key:'paid',label:'Net collected',format:'money'},{key:'balance',label:'Balance',format:'money'}],
  },
  'monthly-revenue': {
    title: 'Monthly receipts and outstanding invoices',
    description: 'Net collected amounts use receipt/refund recording month; outstanding balances use invoice month. Legacy receipt timezones may be unknown; labels are never receipts.',
    filters: ['date_from', 'date_to'],
    columns: [{ key: 'revenue_month', label: 'Month', format: 'month' }, { key: 'collected_total', label: 'Recorded receipts', format: 'money' }, { key: 'outstanding_total', label: 'Outstanding by issue month', format: 'money' }],
  },
};

const state = {
  view: 'dashboard',
  options: null,
  rows: [],
  searchTimer: null,
  sort: null,
  direction: 'asc',
  dashboardRequest: 0,
  moduleRequest: 0,
  reportRequest: 0,
  page: 1,
  pageSize: 25,
  pagination: null,
  appointmentView: 'table',
  queueData: null,
  reportId: 'department-doctor-counts',
  reportPage: 1,
  reportPagination: null,
};

const mainContent = document.getElementById('mainContent');
const modalRoot = document.getElementById('modalRoot');
const toastRegion = document.getElementById('toastRegion');
let modalReturnFocus = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

let hospitalZone = 'Asia/Kolkata';
function todayLocal() {
  const parts = new Intl.DateTimeFormat('en-CA', {timeZone:hospitalZone, year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
  const part = (type) => parts.find(p=>p.type===type).value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}
async function loadHospitalConfig() {
  try { const config = await apiRequest('/api/config'); hospitalZone = config.timezone; refreshConnectionDate(); }
  catch (error) { toast(`Hospital clock unavailable: ${error.message}`, 'error'); }
}

function setPageTitle(title) {
  document.getElementById('pageTitle').textContent = title;
  document.title = `${title} · CarePoint`;
}

function renderNavigation() {
  const nav = document.getElementById('primaryNav');
  nav.innerHTML = NAV_ITEMS.map((item) => `
    <a class="nav-link${state.view === item.id ? ' active' : ''}" href="#${item.id}"
      data-action="navigate" data-view="${item.id}"${state.view === item.id ? ' aria-current="page"' : ''}>
      <span class="nav-icon" aria-hidden="true">${renderIcon(item.icon)}</span>
      <span>${escapeHtml(item.label)}</span>
    </a>`).join('');
  if (window.hmsUser?.role === 'manager') nav.insertAdjacentHTML('afterbegin','<button class="nav-link" data-role-refresh>← Personal workspace</button><button class="nav-link" data-role-logout>Sign out</button>');
}

function setMobileNavigation(open, { restoreFocus = true } = {}) {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.menu-toggle');
  const wasOpen = sidebar.classList.contains('open');
  const isMobile = window.matchMedia('(max-width: 820px)').matches;
  sidebar.classList.toggle('open', open);
  sidebar.inert = isMobile && !open;
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  const icon = toggle.querySelector('[aria-hidden="true"]');
  if (icon) icon.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="${open ? 'M6 6l12 12M18 6L6 18' : 'M4 6h16M4 12h16M4 18h16'}"/></svg>`;
  if (open) {
    (sidebar.querySelector('.nav-link.active') || sidebar.querySelector('.nav-link'))?.focus();
  } else if (restoreFocus && wasOpen) {
    toggle.focus();
  }
}

function syncNavigationBreakpoint() {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.menu-toggle');
  const isMobile = window.matchMedia('(max-width: 820px)').matches;
  if (!isMobile && sidebar.classList.contains('open')) {
    setMobileNavigation(false, { restoreFocus: false });
    return;
  }
  const focusMovesIntoDrawer = isMobile && !sidebar.classList.contains('open')
    && sidebar.contains(document.activeElement);
  sidebar.inert = isMobile && !sidebar.classList.contains('open');
  if (focusMovesIntoDrawer) toggle.focus();
}

async function apiEnvelope(path, options = {}) {
  const sessionMarker=window.hmsCsrf;
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window.hmsCsrf || '', ...(options.headers || {}) },
    });
  } catch (error) {
    throw new Error('The application server could not be reached. Check that Flask is running.');
  }
  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    throw new Error('The server returned an unreadable response.');
  }
  if (sessionMarker && sessionMarker !== window.hmsCsrf) throw new Error('Session changed; stale response ignored.');
  if (!response.ok) {
    if (response.status === 401) window.hmsExpired?.();
    throw new Error(payload?.error?.message || `Request failed (${response.status}).`);
  }
  return payload;
}

async function apiRequest(path, options = {}) {
  return (await apiEnvelope(path, options)).data;
}

function setConnectionState(connected, label) {
  const container = document.getElementById('connectionState');
  container.classList.toggle('connected', Boolean(connected));
  container.classList.toggle('disconnected', !connected);
  document.getElementById('connectionLabel').textContent = label;
}

async function checkConnection() {
  try {
    await apiRequest('/api/health');
    setConnectionState(true, 'Database connected');
  } catch (error) {
    setConnectionState(false, 'Database unavailable');
  }
}

async function loadOptions(force = false) {
  if (state.options && !force) return state.options;
  state.options = await apiRequest('/api/options');
  return state.options;
}

function navigate(view, updateHistory = true) {
  if (window.HMS_ROLE_BOOT && (!window.hmsUser || !window.hmsAdminMode)) return;
  if (view !== 'dashboard' && view !== 'reports' && !MODULES[view]) return;
  const primaryNav = document.getElementById('primaryNav');
  const focusWasInNavigation = primaryNav.contains(document.activeElement);
  const focusWasInMain = mainContent.contains(document.activeElement);
  const navigationWasOpen = document.getElementById('sidebar').classList.contains('open');
  state.view = view;
  state.sort = null;
  state.direction = 'asc';
  state.page = 1;
  state.pagination = null;
  if (view !== 'appointments') state.appointmentView = 'table';
  renderNavigation();
  setMobileNavigation(false, { restoreFocus: false });
  const title = view === 'dashboard' ? 'Dashboard' : view === 'reports' ? 'Reports' : MODULES[view].title;
  setPageTitle(title);
  if (navigationWasOpen || focusWasInMain) document.getElementById('pageTitle').focus();
  else if (focusWasInNavigation) primaryNav.querySelector('.nav-link.active')?.focus();
  if (view === 'dashboard') loadDashboard();
  else if (view === 'reports') loadReports();
  else loadModule();
  if (updateHistory && location.hash !== `#${view}`) history.pushState(null, '', `#${view}`);
}

async function loadDashboard() {
  if (mainContent.contains(document.activeElement)) mainContent.focus();
  const requestId = ++state.dashboardRequest;
  mainContent.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading database summaries…</div>';
  try {
    const data = await apiRequest('/api/dashboard');
    if (state.view !== 'dashboard' || requestId !== state.dashboardRequest) return;
    renderDashboard(data);
  } catch (error) {
    if (state.view === 'dashboard' && requestId === state.dashboardRequest) renderLoadError(error, loadDashboard);
  }
}

function renderDashboard(data) {
  const counts = data.counts || {};
  const cards = [
    ["Today's queue", counts.today_queue_appointments, 'appointments', 'Booked and in progress today', 'appointments', 'queue'],
    ['Active admissions', counts.active_admissions, 'admissions', 'Patients currently admitted', 'admissions'],
    ['Available rooms', counts.available_rooms, 'rooms', 'Ready for admission', 'rooms'],
    ['Pending bills', counts.pending_bills, 'bills', 'Awaiting payment', 'bills'],
  ];
  const supportingTotals = [
    ['Patients', counts.patients],
    ['Doctors', counts.doctors],
    ['Departments', counts.departments],
    ['All appointments', counts.appointments],
    ['Completed visits', counts.completed_appointments],
    ['Cancelled visits', counts.cancelled_appointments],
    ['Occupied rooms', counts.occupied_rooms],
    ['Medicine catalogue', counts.total_medicines],
    ['Low-stock medicines', counts.low_stock_medicines],
    ['Outstanding invoice balance', formatMoney(data.outstanding_total)],
    ['Net collected', formatMoney(data.collected_total)],
  ];
  const recent = data.recent_records || [];
  mainContent.innerHTML = `
    <div class="dashboard-greeting">
      <div><h2>Hospital overview</h2><p>Operational queues first; supporting register totals follow.</p></div>
      <div class="dashboard-mark"><span>Database snapshot · refresh to update</span><button class="button button-secondary button-small" type="button" data-action="refresh">Refresh dashboard</button></div>
    </div>
    <section class="summary-grid" aria-label="Priority queues and room capacity">
      ${cards.map(([label, value, icon, note, view, mode]) => `
        <button class="summary-card summary-card-link" type="button" data-action="${mode === 'queue' ? 'open-appointment-queue' : 'navigate'}" data-view="${escapeHtml(view)}" aria-label="Open ${escapeHtml(label.toLowerCase())}">
          <span class="summary-top"><span class="summary-label">${escapeHtml(label)}</span><span class="summary-icon" aria-hidden="true">${renderIcon(icon)}</span></span>
          <strong class="summary-value">${escapeHtml(value ?? '—')}</strong><span class="summary-note">${escapeHtml(note)}</span>
        </button>`).join('')}
    </section>
    <section class="dashboard-panels" aria-label="Operational work queues">
      <article class="panel">
        <header class="panel-header"><div><h2 class="panel-title">Upcoming appointments</h2><p class="panel-subtitle">Scheduled visits from today onwards</p></div><button class="panel-link" type="button" data-action="navigate" data-view="appointments">View appointments →</button></header>
        <div class="panel-body">${renderSimpleTable(data.upcoming_appointments || [], [
          { key: 'appointment_date', label: 'Date', format: 'date' }, { key: 'appointment_time', label: 'Time' },
          { key: 'patient_name', label: 'Patient', strong: true }, { key: 'doctor_name', label: 'Doctor' },
          { key: 'status', label: 'Status', format: 'status' },
        ], 'No upcoming appointments are scheduled.', 'Upcoming appointments')}</div>
      </article>
      <article class="panel">
        <header class="panel-header"><div><h2 class="panel-title">Outstanding invoices</h2><p class="panel-subtitle">Balance · ${escapeHtml(formatMoney(data.outstanding_total))} total</p></div><button class="panel-link" type="button" data-action="navigate" data-view="bills">View billing →</button></header>
        <div class="panel-body">${renderSimpleTable(data.outstanding_bills || [], [
          { key: 'bill_id', label: 'Bill', format: 'recordId' }, { key: 'patient_name', label: 'Patient', strong: true },
          { key: 'bill_date', label: 'Date', format: 'date' }, { key: 'total_amount', label: 'Amount', format: 'money' },
        ], 'There are no outstanding bills.', 'Outstanding bills')}</div>
      </article>
      <article class="panel">
        <header class="panel-header"><div><h2 class="panel-title">Low-stock medicines</h2><p class="panel-subtitle">Less than ten units recorded</p></div><button class="panel-link" type="button" data-action="navigate" data-view="medicines">Manage inventory →</button></header>
        <div class="panel-body">${renderSimpleTable(data.low_stock_medicines || [], [
          { key: 'medicine_name', label: 'Medicine', strong: true }, { key: 'manufacturer', label: 'Manufacturer' },
          { key: 'stock_quantity', label: 'Stock', format: 'stock' },
        ], 'No medicines are below the low-stock threshold.', 'Low-stock medicines')}</div>
      </article>
      <article class="panel">
        <header class="panel-header"><div><h2 class="panel-title">Recent records</h2><p class="panel-subtitle">Appointments, admissions, prescriptions, and bills</p></div><button class="panel-link" type="button" data-action="navigate" data-view="reports">Open reports →</button></header>
        <div class="panel-body">${recent.length ? `<div class="activity-list">${recent.map((item) => `
          <button class="activity-item" type="button" data-action="navigate" data-view="${escapeHtml(item.resource)}">
            <span class="activity-mark" aria-hidden="true">${escapeHtml(item.activity_type.slice(0, 1))}</span>
            <span class="activity-copy"><strong>${escapeHtml(item.activity_type)} · #${escapeHtml(item.record_id)}</strong><small>${escapeHtml(item.description)}</small></span>
            <time>${escapeHtml(formatDate(item.record_date))}</time>
          </button>`).join('')}</div>` : '<div class="empty-state"><strong>No recent records</strong><span>New dated records will appear here when available.</span></div>'}</div>
      </article>
    </section>
    <section class="dashboard-snapshot" aria-labelledby="dashboardSnapshotTitle">
      <div class="snapshot-heading"><h3 id="dashboardSnapshotTitle">Register and payment totals</h3><p>Supporting figures from this dashboard response</p></div>
      <dl class="snapshot-grid">${supportingTotals.map(([label, value]) => `
        <div class="snapshot-item"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? '—')}</dd></div>`).join('')}
      </dl>
    </section>`;
}

function renderSimpleTable(rows, columns, emptyMessage, tableLabel = 'Records') {
  if (!rows.length) return `<div class="empty-state"><span class="empty-icon" aria-hidden="true">✓</span><strong>All clear</strong><span>${escapeHtml(emptyMessage)}</span></div>`;
  const table = `<table class="data-table"><thead><tr>${columns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join('')}</tr></thead><tbody>
    ${rows.map((row) => `<tr>${columns.map((column) => `<td>${renderCell(row[column.key], column)}</td>`).join('')}</tr>`).join('')}
    </tbody></table>`;
  return tableRegion(table, `${tableLabel} table`);
}

function tableRegion(table, label) {
  return `<div class="table-region"><p class="table-scroll-hint">Swipe or scroll horizontally to view all columns.</p><div class="table-wrap" role="region" tabindex="0" aria-label="${escapeHtml(label)}. Scroll horizontally to see all columns on narrow screens.">${table}</div></div>`;
}

async function loadModule() {
  if (mainContent.contains(document.activeElement)) mainContent.focus();
  const view = state.view;
  const config = MODULES[view];
  if (!config) return;
  mainContent.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading records…</div>';
  try {
    const options = await loadOptions();
    if (state.view !== view) return;
    mainContent.innerHTML = moduleShell(config, options);
    syncAppointmentControls();
    await refreshModuleRows();
  } catch (error) {
    if (state.view === view) renderLoadError(error, loadModule);
  }
}

function moduleShell(config, options) {
  return `
    <section class="page-heading"><div><h2>${escapeHtml(config.title)}</h2><p>${escapeHtml(config.description)}</p></div>
      <div class="page-actions"><button class="button button-primary" type="button" data-action="add">${escapeHtml(config.addLabel)}</button></div>
    </section>
    <section aria-label="${escapeHtml(config.title)} records">
      <div class="toolbar"><div class="toolbar-left">
        <label class="search-wrap"><span class="visually-hidden">Search ${escapeHtml(config.title)}</span><input type="search" id="moduleSearch" placeholder="Search ${escapeHtml(config.title.toLowerCase())}…" autocomplete="off"></label>
        ${config.filters.map((filter) => renderFilter(filter, options)).join('')}
        ${config.endpoint === 'appointments' ? `<label class="queue-date-control" id="queueDateControl"${state.appointmentView === 'queue' ? '' : ' hidden'}>Queue date<input class="control" type="date" id="queueDate" value="${escapeHtml(todayLocal())}" aria-label="Queue date"></label>` : ''}
      </div><div class="toolbar-right">${config.endpoint === 'appointments' ? `<div class="appointment-view-switch" role="group" aria-label="Appointment views">
        ${[['table', 'Table'], ['agenda', 'Agenda'], ['queue', 'Queue']].map(([mode, label]) => `<button class="button button-secondary button-small appointment-view-button" type="button" data-action="appointment-mode" data-mode="${mode}" aria-pressed="${state.appointmentView === mode}">${label}</button>`).join('')}
      </div>` : ''}<button class="button button-secondary button-small" type="button" data-action="refresh">Refresh</button></div></div>
      <div id="moduleTable" aria-live="polite"><div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading…</div></div>
    </section>`;
}

function syncAppointmentControls() {
  const isQueue = state.view === 'appointments' && state.appointmentView === 'queue';
  document.querySelectorAll('[data-filter-wrap]').forEach((wrapper) => {
    wrapper.hidden = isQueue && wrapper.dataset.filterWrap !== 'doctor_id';
  });
  const queueDate = document.getElementById('queueDateControl');
  if (queueDate) queueDate.hidden = !isQueue;
  document.querySelectorAll('[data-action="appointment-mode"]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.mode === state.appointmentView));
  });
}

function renderFilter(filter, options) {
  const label = filter.label;
  let control;
  if (filter.type === 'date') {
    control = `<label class="visually-hidden" for="filter-${escapeHtml(filter.key)}">${escapeHtml(label)}</label><input class="control module-filter" type="date" id="filter-${escapeHtml(filter.key)}" data-filter="${escapeHtml(filter.key)}" aria-label="${escapeHtml(label)}">`;
  } else {
    const choices = filter.source ? (options[filter.source] || []).map((option) => ({ value: option.id, label: option.label })) : (filter.choices ? CHOICES[filter.choices] || filter.choices : []);
    control = `<label class="visually-hidden" for="filter-${escapeHtml(filter.key)}">${escapeHtml(label)}</label><select class="control module-filter" id="filter-${escapeHtml(filter.key)}" data-filter="${escapeHtml(filter.key)}"><option value="">${escapeHtml(label)}</option>${choices.map((choice) => `<option value="${escapeHtml(choice.value)}">${escapeHtml(choice.label)}</option>`).join('')}</select>`;
  }
  return `<span class="module-filter-wrap" data-filter-wrap="${escapeHtml(filter.key)}">${control}</span>`;
}

async function refreshModuleRows() {
  const view = state.view;
  const config = MODULES[view];
  if (!config || !document.getElementById('moduleTable')) return;
  if (view === 'appointments' && state.appointmentView === 'queue') {
    return refreshAppointmentQueue();
  }
  const requestId = ++state.moduleRequest;
  const container = document.getElementById('moduleTable');
  container.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading records…</div>';
  const params = new URLSearchParams();
  const search = document.getElementById('moduleSearch')?.value.trim();
  if (search) params.set('q', search);
  document.querySelectorAll('.module-filter').forEach((select) => {
    if (select.value) params.set(select.dataset.filter, select.value);
  });
  if (state.sort) {
    params.set('sort', state.sort);
    params.set('direction', state.direction);
  }
  params.set('page', String(state.page));
  params.set('page_size', String(state.pageSize));
  try {
    const payload = await apiEnvelope(`/api/${config.endpoint}?${params.toString()}`);
    if (state.view !== view || requestId !== state.moduleRequest || !document.getElementById('moduleTable')) return;
    const rows = payload.data || [];
    state.pagination = payload.meta?.pagination || null;
    state.rows = rows;
    container.innerHTML = renderModuleTable(rows, config);
  } catch (error) {
    if (state.view !== view || requestId !== state.moduleRequest) return;
    container.innerHTML = `<div class="error-state"><strong>Records could not be loaded</strong><p>${escapeHtml(error.message)}</p><button class="button button-secondary button-small" type="button" data-action="refresh">Try again</button></div>`;
  }
}

async function refreshAppointmentQueue() {
  const requestId = ++state.moduleRequest;
  const container = document.getElementById('moduleTable');
  if (!container) return;
  container.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading the selected appointment queue…</div>';
  const params = new URLSearchParams();
  params.set('date', document.getElementById('queueDate')?.value || todayLocal());
  const doctorId = document.getElementById('filter-doctor_id')?.value;
  if (doctorId) params.set('doctor_id', doctorId);
  try {
    const payload = await apiEnvelope(`/api/appointments/queue?${params.toString()}`);
    if (state.view !== 'appointments' || state.appointmentView !== 'queue'
      || requestId !== state.moduleRequest || !document.getElementById('moduleTable')) return;
    state.queueData = payload.data || null;
    state.rows = state.queueData?.rows || [];
    state.pagination = null;
    container.innerHTML = renderAppointmentQueue(state.queueData || {}, MODULES.appointments);
  } catch (error) {
    if (state.view !== 'appointments' || state.appointmentView !== 'queue' || requestId !== state.moduleRequest) return;
    container.innerHTML = `<div class="error-state"><strong>Appointment queue could not be loaded</strong><p>${escapeHtml(error.message)}</p><button class="button button-secondary button-small" type="button" data-action="refresh">Try again</button></div>`;
  }
}

async function loadReports() {
  if (mainContent.contains(document.activeElement)) mainContent.focus();
  const requestId = ++state.reportRequest;
  mainContent.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading database reports…</div>';
  try {
    const options = await loadOptions();
    if (state.view !== 'reports' || requestId !== state.reportRequest) return;
    renderReportShell(options);
    await refreshReportRows();
  } catch (error) {
    if (state.view === 'reports' && requestId === state.reportRequest) renderLoadError(error, loadReports);
  }
}

function renderReportFilter(key, options) {
  if (key === 'date_from' || key === 'date_to') {
    const label = key === 'date_from' ? 'From date' : 'To date';
    return `<label class="report-filter-label">${label}<input class="control report-filter" type="date" data-filter="${key}" aria-label="${label}"></label>`;
  }
  const source = ({ patient_id: 'patients', doctor_id: 'doctors', medicine_id: 'medicines', room_id: 'rooms' })[key];
  if (source) {
    const choices = options[source] || [];
    const label = ({ patient_id: 'All patients', doctor_id: 'All doctors', medicine_id: 'All medicines', room_id: 'All rooms' })[key];
    return `<label class="visually-hidden" for="report-${key}">${label}</label><select class="control report-filter" id="report-${key}" data-filter="${key}"><option value="">${label}</option>${choices.map((option) => `<option value="${escapeHtml(option.id)}">${escapeHtml(option.label)}</option>`).join('')}</select>`;
  }
  const choices = key === 'status' ? CHOICES.appointment_status : CHOICES.ledger_status;
  const label = key === 'status' ? 'All statuses' : 'All payment statuses';
  return `<label class="visually-hidden" for="report-${key}">${label}</label><select class="control report-filter" id="report-${key}" data-filter="${key}"><option value="">${label}</option>${choices.map((choice) => `<option value="${escapeHtml(choice.value)}">${escapeHtml(choice.label)}</option>`).join('')}</select>`;
}

function renderReportShell(options) {
  const config = REPORTS[state.reportId];
  mainContent.innerHTML = `
    <section class="page-heading"><div><h2 id="reportTitle">${escapeHtml(config.title)}</h2><p id="reportDescription">${escapeHtml(config.description)}</p></div>
      <div class="report-picker"><label for="reportSelect">Choose report</label><select class="control" id="reportSelect">${Object.entries(REPORTS).map(([key, report]) => `<option value="${escapeHtml(key)}"${key === state.reportId ? ' selected' : ''}>${escapeHtml(report.title)}</option>`).join('')}</select></div>
    </section>
    <section aria-label="Database reports"><div class="toolbar"><div class="toolbar-left" id="reportFilters">${config.filters.map((key) => renderReportFilter(key, options)).join('')}</div>
      <div class="toolbar-right"><button class="button button-secondary button-small" type="button" data-action="export-report-csv">Export filtered CSV</button><button class="button button-secondary button-small" type="button" data-action="refresh-report">Refresh report</button></div></div>
      <div id="reportTable" aria-live="polite"><div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading report…</div></div>
    </section>`;
}

async function refreshReportRows() {
  const requestId = ++state.reportRequest;
  const config = REPORTS[state.reportId];
  const container = document.getElementById('reportTable');
  if (!config || !container) return;
  container.innerHTML = '<div class="loading-state"><span class="spinner" aria-hidden="true"></span> Querying database…</div>';
  const params = new URLSearchParams();
  document.querySelectorAll('.report-filter').forEach((control) => {
    if (control.value) params.set(control.dataset.filter, control.value);
  });
  params.set('page', String(state.reportPage));
  params.set('page_size', String(state.pageSize));
  try {
    const payload = await apiEnvelope(`/api/reports/${encodeURIComponent(state.reportId)}?${params.toString()}`);
    if (state.view !== 'reports' || requestId !== state.reportRequest || !document.getElementById('reportTable')) return;
    state.reportPagination = payload.meta?.pagination || null;
    container.innerHTML = renderReportTable(payload.data || [], config);
  } catch (error) {
    if (state.view !== 'reports' || requestId !== state.reportRequest) return;
    container.innerHTML = `<div class="error-state"><strong>Report could not be loaded</strong><p>${escapeHtml(error.message)}</p><button class="button button-secondary button-small" type="button" data-action="refresh-report">Try again</button></div>`;
  }
}

async function exportReportCsv() {
  const params = new URLSearchParams();
  document.querySelectorAll('.report-filter').forEach((control) => {
    if (control.value) params.set(control.dataset.filter, control.value);
  });
  const endpoint = `/api/reports/${encodeURIComponent(state.reportId)}/csv?${params.toString()}`;
  try {
    const response = await fetch(endpoint, { headers: { Accept: 'text/csv, application/json' } });
    if (!response.ok) {
      let message = `CSV export failed (${response.status}).`;
      try { message = (await response.json())?.error?.message || message; } catch (error) { /* Keep the safe fallback. */ }
      throw new Error(message);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') || '';
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || `${state.reportId}.csv`;
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    toast(`Exported ${REPORTS[state.reportId].title} as CSV.`);
  } catch (error) {
    toast(error.message, 'error');
  }
}

function renderReportTable(rows, config) {
  if (!rows.length) {
    return `<div class="empty-state"><span class="empty-icon" aria-hidden="true">▥</span><strong>No report rows</strong><span>No database records match this report and its filters.</span></div>${renderPagination(state.reportPagination, 'report')}`;
  }
  const head = config.columns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join('');
  const body = rows.map((row) => `<tr>${config.columns.map((column) => `<td>${renderCell(row[column.key], column, row)}</td>`).join('')}</tr>`).join('');
  return `${tableRegion(`<table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`, `${config.title} report`)}${renderPagination(state.reportPagination, 'report')}`;
}

function renderModuleTable(rows, config) {
  if (!rows.length) {
    return `<div class="empty-state"><span class="empty-icon" aria-hidden="true">＋</span><strong>No ${escapeHtml(config.endpoint)} found</strong><span>Try a different search or add the first ${escapeHtml(config.singular)}.</span></div>${renderPagination(state.pagination, 'module')}`;
  }
  if (config.endpoint === 'appointments' && state.appointmentView === 'agenda') {
    return `${renderAppointmentAgenda(rows, config)}${renderPagination(state.pagination, 'module')}`;
  }
  const headers = config.columns.map((column) => {
    if (!column.sort) return `<th scope="col"${column.align === 'right' ? ' class="actions-head"' : ''}>${escapeHtml(column.label)}</th>`;
    const active = state.sort === column.key;
    const marker = active ? (state.direction === 'asc' ? '↑' : '↓') : '↕';
    const sortState = active ? ` aria-sort="${state.direction === 'asc' ? 'ascending' : 'descending'}"` : '';
    const sortLabel = active
      ? `${column.label}, sorted ${state.direction === 'asc' ? 'ascending' : 'descending'}`
      : `Sort by ${column.label} ascending`;
    return `<th scope="col"${sortState}><button class="sort-button" type="button" data-action="sort" data-sort="${escapeHtml(column.key)}" aria-label="${escapeHtml(sortLabel)}">${escapeHtml(column.label)} <span class="sort-indicator" aria-hidden="true">${marker}</span></button></th>`;
  }).join('');
  const body = rows.map((row) => `<tr>${config.columns.map((column) => `<td${column.align === 'right' ? ' class="actions-head"' : ''}>${renderCell(row[column.key], column, row)}</td>`).join('')}<td class="actions-head"><div class="row-actions">${renderRowActions(state.view, config, row)}</div></td></tr>`).join('');
  const table = `<table class="data-table"><thead><tr>${headers}<th scope="col" class="actions-head">Actions</th></tr></thead><tbody>${body}</tbody></table>`;
  return `${tableRegion(table, `${config.title} records`)}${renderPagination(state.pagination, 'module')}`;
}

function renderPagination(info, context) {
  if (!info) return '';
  const start = info.total === 0 ? 0 : ((info.page - 1) * info.page_size) + 1;
  const end = Math.min(info.total, info.page * info.page_size);
  return `<div class="table-footer pagination-footer">
    <span>Showing ${start}–${end} of ${info.total} records</span>
    <div class="pagination-controls">
      <label class="page-size-label">Rows <select class="control page-size-select" data-action="page-size" data-context="${context}" aria-label="Rows per page">${[10, 25, 50, 100].map((size) => `<option value="${size}"${info.page_size === size ? ' selected' : ''}>${size}</option>`).join('')}</select></label>
      <button class="button button-secondary button-small" type="button" data-action="page" data-context="${context}" data-page="${Math.max(1, info.page - 1)}"${info.page <= 1 ? ' disabled' : ''} aria-label="Previous page">←</button>
      <span class="page-indicator">Page ${info.page} of ${info.pages}</span>
      <button class="button button-secondary button-small" type="button" data-action="page" data-context="${context}" data-page="${Math.min(info.pages, info.page + 1)}"${info.page >= info.pages ? ' disabled' : ''} aria-label="Next page">→</button>
    </div>
  </div>`;
}

function renderAppointmentAgenda(rows, config) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = String(row.appointment_date).slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  const cards = [...groups.entries()].sort(([first], [second]) => first.localeCompare(second)).map(([day, items]) => `
    <section class="agenda-day"><header><h3>${escapeHtml(formatDate(day))}</h3><span>${items.length} ${items.length === 1 ? 'visit' : 'visits'}</span></header>
      <div class="agenda-events">${items.sort((a, b) => String(a.appointment_time).localeCompare(String(b.appointment_time))).map((row) => `
        <article class="agenda-event"><time>${escapeHtml(row.appointment_time)}</time><div class="agenda-event-copy"><strong>${escapeHtml(row.patient_name)}</strong><span>${escapeHtml(row.doctor_name)} · ${escapeHtml(row.department_name)}</span></div>${statusPill(row.status)}<div class="row-actions">${renderRowActions('appointments', config, row)}</div></article>`).join('')}</div>
    </section>`).join('');
  return `<section class="agenda-list" aria-label="Appointment agenda">${cards}</section>`;
}

function renderAppointmentQueue(queue, config) {
  const allRows = queue.rows || [];
  const query = document.getElementById('moduleSearch')?.value.trim().toLocaleLowerCase() || '';
  const rows = query ? allRows.filter((row) => [
    row.patient_name, row.doctor_name, row.department_name, row.appointment_time,
    row.status, row.appointment_id,
  ].some((value) => String(value ?? '').toLocaleLowerCase().includes(query))) : allRows;
  const counts = queue.counts || {};
  const metrics = ['Scheduled', 'Checked In', 'Waiting', 'In Consultation', 'Completed', 'Cancelled', 'No-show'];
  const next = queue.next_patient;
  const table = rows.length ? tableRegion(`<table class="data-table"><thead><tr>
      <th scope="col">Time</th><th scope="col">Patient</th><th scope="col">Doctor</th>
      <th scope="col">Department</th><th scope="col">Status</th><th scope="col" class="actions-head">Actions</th>
    </tr></thead><tbody>${rows.map((row) => `<tr>
      <td>${escapeHtml(row.appointment_time)}</td><td><strong>${escapeHtml(row.patient_name)}</strong></td>
      <td>${escapeHtml(row.doctor_name)}</td><td>${escapeHtml(row.department_name)}</td>
      <td>${statusPill(row.status)}</td><td class="actions-head"><div class="row-actions">${renderRowActions('appointments', config, row)}</div></td>
    </tr>`).join('')}</tbody></table>`, 'Appointment queue')
    : `<div class="empty-state"><strong>${allRows.length ? 'No matching appointments' : 'No appointments for this queue'}</strong><span>${allRows.length ? 'Try a different patient, doctor, or status search.' : 'Choose another date or doctor, or book an appointment.'}</span></div>`;

  return `<section class="appointment-queue" aria-label="Daily appointment queue">
    <article class="queue-highlight" aria-live="polite"><div><span class="queue-eyebrow">Next to be seen · ${escapeHtml(formatDate(queue.date))}</span>
      ${next ? `<h3>${escapeHtml(next.patient_name)}</h3><p>${escapeHtml(next.appointment_time)} · ${escapeHtml(next.doctor_name)} · ${escapeHtml(next.status)}</p>` : '<h3>No patient is waiting or scheduled next</h3><p>There are no waiting, checked-in, or scheduled visits for this date and doctor.</p>'}
    </div><span class="queue-next-mark" aria-hidden="true">${next ? escapeHtml(next.appointment_time) : '—'}</span></article>
    <p class="queue-order-note">Queue order is Waiting, then Checked In, then Scheduled; each group follows booked appointment time. Arrival order and triage priority are not recorded.</p>
    <section class="queue-stat-grid" aria-label="Appointment counts by status">${metrics.map((status) => `<article class="queue-stat"><span>${escapeHtml(status)}</span><strong>${escapeHtml(counts[status] ?? 0)}</strong></article>`).join('')}</section>
    <section class="queue-list" aria-label="Appointments for ${escapeHtml(formatDate(queue.date))}">
      <div class="queue-list-heading"><h3>Appointments for ${escapeHtml(formatDate(queue.date))}</h3><span>${rows.length} shown${rows.length !== allRows.length ? ` · ${allRows.length} total` : ''}</span></div>
      ${table}
    </section>
  </section>`;
}

function renderRowActions(view, config, row) {
  const id = row[primaryKey(view)];
  const safeId = escapeHtml(id);
  const primaryColumn = config.columns.find((column) => column.strong) || config.columns[0];
  const recordLabel = `${config.singular} ${row[primaryColumn.key] ?? `#${id}`} (#${id})`;
  const accessibleRecordLabel = escapeHtml(recordLabel);
  const actions = [];
  if (view === 'patients') {
    actions.push(`<button class="button button-secondary button-small" type="button" data-action="details" data-id="${safeId}" aria-label="View history for ${accessibleRecordLabel}">History</button>`);
  } else {
    actions.push(`<button class="button button-secondary button-small" type="button" data-action="view-record" data-view="${escapeHtml(view)}" data-id="${safeId}" aria-label="View ${accessibleRecordLabel}">View</button>`);
  }
  if (view === 'admissions' && !row.discharge_date) {
    actions.push(`<button class="button button-secondary button-small" type="button" data-action="move-room" data-id="${safeId}" aria-label="Move ${accessibleRecordLabel} to another room">Move room</button>`);
    actions.push(`<button class="button button-secondary button-small" type="button" data-action="discharge" data-id="${safeId}" aria-label="Discharge ${accessibleRecordLabel}">Discharge</button>`);
  }
  if (view === 'medicines' && !window.hmsUser) actions.push(`<button class="button button-secondary button-small" type="button" data-action="stock" data-id="${safeId}" aria-label="Adjust stock for ${accessibleRecordLabel}">Adjust stock</button>`);
  if (view === 'appointments') {
    const appointmentDay = String(row.appointment_date || '').slice(0, 10);
    if (row.status === 'Scheduled') {
      if (appointmentDay === todayLocal()) {
        actions.push(`<button class="button button-secondary button-small" type="button" data-action="appointment-status" data-status="Checked In" data-id="${safeId}" aria-label="Check in ${accessibleRecordLabel}">Check in</button>`);
      } else if (appointmentDay && appointmentDay < todayLocal()) {
        actions.push(`<button class="button button-secondary button-small" type="button" data-action="appointment-status" data-status="No-show" data-id="${safeId}" aria-label="Mark ${accessibleRecordLabel} as no-show">Mark no-show</button>`);
      }
      actions.push(`<button class="button button-secondary button-small" type="button" data-action="appointment-status" data-status="Cancelled" data-id="${safeId}" aria-label="Cancel ${accessibleRecordLabel}">Cancel</button>`);
    } else {
      const nextAction = {
        'Checked In': ['Waiting', 'Add to waiting list'],
        'Waiting': ['In Consultation', 'Start consultation'],
        'In Consultation': ['Completed', 'Complete visit'],
      }[row.status];
      if (nextAction) {
        actions.push(`<button class="button button-secondary button-small" type="button" data-action="appointment-status" data-status="${escapeHtml(nextAction[0])}" data-id="${safeId}" aria-label="${escapeHtml(nextAction[1])} for ${accessibleRecordLabel}">${escapeHtml(nextAction[1])}</button>`);
      }
    }
  }
  if (!config.noEdit && (view !== 'appointments' || row.status === 'Scheduled')) {
    actions.push(`<button class="button button-secondary button-small" type="button" data-action="edit" data-id="${safeId}" aria-label="Edit ${accessibleRecordLabel}">Edit</button>`);
  }
  if (!config.noDelete && view !== 'appointments' && (view !== 'admissions' || row.discharge_date)) {
    actions.push(`<button class="button button-danger button-small" type="button" data-action="delete" data-id="${safeId}" aria-label="Delete ${accessibleRecordLabel}">Delete</button>`);
  }
  return actions.join('');
}

function renderCell(value, column, row = {}) {
  if (column.key === 'admission_state') {
    const status = row.discharge_date ? 'Discharged' : 'Active';
    return `<span class="status-pill ${status === 'Active' ? 'status-available' : 'status-maintenance'}">${status}</span>`;
  }
  if (value === null || value === undefined || value === '') return '<span class="muted-value">—</span>';
  if (column.format === 'date') return escapeHtml(formatDate(value));
  if (column.format === 'month') return escapeHtml(formatMonth(value));
  if (column.format === 'money') return `<strong>${escapeHtml(formatMoney(value))}</strong>`;
  if (column.format === 'recordId') return `<span class="record-number">#${escapeHtml(String(value).padStart(4, '0'))}</span>`;
  if (column.format === 'status') return statusPill(value);
  if (column.format === 'gender') return escapeHtml(({ M: 'Male', F: 'Female', O: 'Other' })[value] || value);
  if (column.format === 'stock') {
    const low = Number(value) < 10;
    return `<span class="stock-value${low ? ' stock-low' : ''}">${escapeHtml(value)}${low ? ' <span class="stock-warning">Low</span>' : ''}</span>`;
  }
  return column.strong ? `<strong>${escapeHtml(value)}</strong>` : escapeHtml(value);
}

function statusPill(value) {
  const className = `status-${String(value).toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return `<span class="status-pill ${escapeHtml(className)}">${escapeHtml(value)}</span>`;
}

function moneyCents(value) {
  const text = String(value ?? '');
  if (!/^-?\d+(?:\.\d{1,2})?$/.test(text)) throw new Error('Invalid decimal money value');
  const negative = text.startsWith('-');
  const [whole, fraction = ''] = text.replace(/^-/, '').split('.');
  const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2,'0'));
  return negative ? -cents : cents;
}
function centsText(cents) { return `${cents / 100n}.${String(cents % 100n).padStart(2,'0')}`; }
function sumMoney(values) { return centsText(values.reduce((sum,value)=>sum+moneyCents(value || '0'),0n)); }
function formatMoney(value) {
  try {
    let cents = moneyCents(value); const sign = cents < 0n ? '-' : ''; if(cents<0n)cents=-cents;
    return `${sign}₹${new Intl.NumberFormat('en-IN').format(cents / 100n)}.${String(cents % 100n).padStart(2,'0')}`;
  } catch { return '—'; }
}

function formatDate(value) {
  if (!value) return '—';
  const datePart = String(value).slice(0, 10);
  const parsed = new Date(`${datePart}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(parsed);
}

function formatMonth(value) {
  if (!value) return '—';
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.getTime())
    ? escapeHtml(value)
    : new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' }).format(parsed);
}

function renderLoadError(error, retry) {
  mainContent.innerHTML = `<div class="error-state"><span class="empty-icon" aria-hidden="true">!</span><strong>Could not load hospital data</strong><p>${escapeHtml(error.message)}<br>Confirm the configured database is reachable and the local connection variables are set.</p><button class="button button-primary" type="button" data-action="retry">Try again</button></div>`;
}

function toast(message, kind = 'success') {
  const item = document.createElement('div');
  item.className = `toast${kind === 'error' ? ' error' : ''}`;
  item.innerHTML = `<span class="toast-mark" aria-hidden="true">${kind === 'error' ? '!' : '✓'}</span><span>${escapeHtml(message)}</span>`;
  toastRegion.appendChild(item);
  window.setTimeout(() => item.remove(), 4800);
}

function resolveChoices(field, options, record) {
  let choices = field.choices ? [...(CHOICES[field.choices] || [])] : [];
  if (field.source) {
    choices = (options[field.source] || []).map((option) => {
      const label = (field.source === 'doctors' && option.department_name)
        ? `${option.label} (${option.department_name})`
        : option.label;
      return { value: option.id, label };
    });
  }
  if (field.key === 'availability_status') {
    if (!record || record.availability_status !== 'Occupied') {
      choices = choices.filter((choice) => choice.value !== 'Occupied');
    } else if (!choices.some((choice) => choice.value === 'Occupied')) {
      choices.push({ value: 'Occupied', label: 'Occupied (active admission)' });
    }
  }
  return choices;
}

function fieldValue(field, record) {
  if (record && record[field.key] !== undefined && record[field.key] !== null) return String(record[field.key]);
  if (field.default !== undefined) return String(field.default);
  if (field.key.endsWith('_date') || field.key === 'bill_date' || field.key === 'prescription_date') return todayLocal();
  return '';
}

function renderField(field, options, record) {
  const id = `form-${field.key}`;
  const required = Boolean(field.required);
  const label = `${escapeHtml(field.label)}${required ? ' <span class="required-mark" aria-hidden="true">*</span>' : ''}`;
  const requiredAttr = required ? ' required' : '';
  const hintId = field.hint ? `${id}-hint` : '';
  const describedByAttr = hintId ? ` aria-describedby="${hintId}"` : '';
  let control = '';
  const value = fieldValue(field, record);
  if (field.type === 'select' || field.type === 'related') {
    const choices = resolveChoices(field, options, record);
    const blank = `<option value=""${value === '' ? ' selected' : ''}>Select…</option>`;
    const select = `<select class="form-control" id="${id}" name="${escapeHtml(field.key)}"${requiredAttr}${describedByAttr}>${blank}${choices.map((choice) => `<option value="${escapeHtml(choice.value)}"${String(choice.value) === value ? ' selected' : ''}>${escapeHtml(choice.label)}</option>`).join('')}</select>`;
    control = field.type === 'related'
      ? `<div class="related-select"><input class="form-control related-search" type="search" data-related-search="${id}" aria-label="Search ${escapeHtml(field.label)} options" placeholder="Type to filter ${escapeHtml(field.label.toLowerCase())}…">${select}</div>`
      : select;
  } else if (field.type === 'textarea') {
    control = `<textarea class="form-control" id="${id}" name="${escapeHtml(field.key)}" maxlength="${field.maxLength || ''}" placeholder="${escapeHtml(field.placeholder || '')}"${requiredAttr}${describedByAttr}>${escapeHtml(value)}</textarea>`;
  } else {
    const type = field.type || 'text';
    const extras = [
      field.maxLength ? `maxlength="${field.maxLength}"` : '',
      field.min !== undefined ? `min="${escapeHtml(field.min)}"` : '',
      field.step ? `step="${escapeHtml(field.step)}"` : '',
      field.placeholder ? `placeholder="${escapeHtml(field.placeholder)}"` : '',
      type === 'date' && field.key === 'date_of_birth' ? `max="${todayLocal()}"` : '',
      type === 'date' && field.key === 'appointment_date' && (!record || record.status === 'Scheduled') ? `min="${todayLocal()}"` : '',
      type === 'date' && ['admission_date', 'prescription_date', 'bill_date'].includes(field.key) ? `max="${todayLocal()}"` : '',
    ].filter(Boolean).join(' ');
    control = `<input class="form-control" type="${escapeHtml(type)}" id="${id}" name="${escapeHtml(field.key)}" value="${escapeHtml(value)}" ${extras}${requiredAttr}${describedByAttr}>`;
  }
  const hint = field.hint ? `<small class="field-hint" id="${hintId}">${escapeHtml(field.hint)}</small>` : '';
  return `<div class="form-field${field.full ? ' full-width' : ''}"><label for="${id}">${label}</label>${control}${hint}</div>`;
}

async function openForm(view, record = null) {
  modalReturnFocus = document.activeElement;
  const config = MODULES[view];
  try {
    const options = await loadOptions(true);
    const visibleFields = config.fields.filter((field) => !(view === 'bills' && record && (field.key === 'bill_date' || (moneyCents(record.paid || '0') > 0n && field.key.endsWith('_charge')))) && !(view === 'medicines' && record && field.key === 'stock_quantity') && !(record && ['bills', 'prescriptions'].includes(view) && field.key === 'patient_id'));
    const ownerNotice = record && ['bills', 'prescriptions'].includes(view)
      ? `<div class="form-field full-width"><strong>Patient: ${escapeHtml(record.patient_name || `#${record.patient_id}`)}</strong><small class="field-hint">Patient ownership cannot be changed after creation.</small></div>` : '';
    const formFields = ownerNotice + visibleFields.map((field) => renderField(field, options, record)).join('');
    const totalPreview = view === 'bills' ? `<div class="form-field full-width"><div class="total-preview"><span>Calculated bill total</span><strong id="billTotalPreview">${escapeHtml(formatMoney(sumMoney([record?.consultation_charge, record?.room_charge, record?.medicine_charge])))}</strong></div><small class="field-hint">Base charges only; invoice total also includes additional items. Invoice date and legacy label cannot be edited.</small></div>` : '';
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="formTitle"><header class="modal-header"><div><h2 id="formTitle">${record ? 'Edit' : 'Add'} ${escapeHtml(config.singular)}</h2><p>${record ? 'Update the selected record.' : 'Enter the details below. Related records are selected from the database.'}</p></div><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header>
      <div class="modal-body"><div id="formError" class="form-error" role="alert" hidden></div><form id="recordForm" data-module="${escapeHtml(view)}" data-id="${record ? escapeHtml(record[primaryKey(view)]) : ''}"><div class="form-grid">${formFields}${totalPreview}</div><footer class="modal-footer"><button class="button button-secondary" type="button" data-action="close-modal">Cancel</button><button class="button button-secondary" type="reset">Reset</button><button class="button button-primary" type="submit">${record ? 'Save changes' : 'Create record'}</button></footer></form></div></section></div>`;
    document.getElementById('modalRoot').querySelector('input,select,textarea')?.focus();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function primaryKey(view) {
  return ({ departments: 'department_id', doctors: 'doctor_id', patients: 'patient_id', appointments: 'appointment_id', rooms: 'room_id', admissions: 'admission_id', medicines: 'medicine_id', prescriptions: 'prescription_id', bills: 'bill_id' })[view];
}

async function openPatientHistory(patientId) {
  modalReturnFocus = document.activeElement;
  modalRoot.innerHTML = '<div class="modal-backdrop"><section class="modal-card modal-wide" role="dialog" aria-modal="true" aria-label="Patient record"><div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading patient history…</div></section></div>';
  focusModal();
  try {
    const data = await apiRequest(`/api/patients/${patientId}/summary`);
    const patient = data.patient;
    const fields = [
      ['Patient ID', `#${String(patient.patient_id).padStart(4, '0')}`], ['Name', patient.patient_name],
      ['Date of birth', formatDate(patient.date_of_birth)], ['Gender', ({ M: 'Male', F: 'Female', O: 'Other' })[patient.gender] || patient.gender],
      ['Phone', patient.phone || '—'], ['Blood group', patient.blood_group || '—'], ['Address', patient.address || '—'],
    ];
    const timelineColumns = [
      { key: 'date', label: 'Date', format: 'date' }, { key: 'time', label: 'Time' },
      { key: 'type', label: 'Record', strong: true }, { key: 'details', label: 'Details' },
      { key: 'status', label: 'Recorded status' },
    ];
    const timeline = data.timeline || [];
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card modal-wide patient-chart-printable" role="dialog" aria-modal="true" aria-labelledby="patientHistoryTitle"><header class="modal-header"><div><h2 id="patientHistoryTitle">Patient record</h2><p>Retained history assembled from the authorized database records shown below.</p></div><div class="print-actions"><button class="button button-primary button-small" type="button" data-action="print-patient">Print patient record</button><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></div></header><div class="modal-body"><article class="detail-card"><h3>${escapeHtml(patient.patient_name)}</h3><div class="detail-grid">${fields.map(([label, value]) => `<div class="detail-item"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join('')}</div></article><p class="chart-disclaimer">${data.consultations ? 'Includes released consultations, laboratory results, ward observations and explicit dispensing events. An instruction alone never proves dispensing. Triage priority is not inferred.' : 'Legacy administrative history only: no diagnosis, triage or dispensing is inferred.'}</p><section class="detail-section patient-timeline"><div class="detail-section-header"><h3>Chronological record</h3><span class="field-hint">${timeline.length} events</span></div>${renderSimpleTable(timeline, timelineColumns, 'No appointment, admission, prescription, or billing history is on file.', 'Patient record timeline')}</section><footer class="modal-footer print-actions"><button class="button button-primary" type="button" data-action="print-patient">Print patient record</button><button class="button button-secondary" type="button" data-action="close-modal">Close</button></footer></div></section></div>`;
    focusModal();
  } catch (error) {
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-label="Patient record"><header class="modal-header"><h2>Patient record</h2><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header><div class="error-state"><strong>History could not be loaded</strong><p>${escapeHtml(error.message)}</p></div></section></div>`;
    focusModal();
  }
}

function formatDetailValue(key, value) {
  if (value === null || value === undefined || value === '') return '—';
  if (key.endsWith('_date') || key === 'date_of_birth') return formatDate(value);
  if (key.includes('charge') || ['billed','paid','balance','item_total','total_amount','price','unit_price','line_total','amount'].includes(key)) return formatMoney(value);
  if (key === 'gender') return ({ M: 'Male', F: 'Female', O: 'Other' })[value] || value;
  return String(value);
}

function openRecordDetails(view, recordId) {
  modalReturnFocus = document.activeElement;
  const config = MODULES[view];
  modalRoot.innerHTML = '<div class="modal-backdrop"><section class="modal-card" role="dialog" aria-modal="true" aria-label="Record details"><div class="loading-state"><span class="spinner" aria-hidden="true"></span> Loading record details…</div></section></div>';
  focusModal();
  apiRequest(`/api/details/${encodeURIComponent(view)}/${encodeURIComponent(recordId)}`).then((payload) => {
    const record = payload.record || {};
    const related = payload.related || {};
    const fields = Object.entries(record).map(([key, value]) => {
      const isStatus = ['status', 'availability_status', 'payment_status'].includes(key);
      const formatted = isStatus ? statusPill(value) : escapeHtml(formatDetailValue(key, value));
      return `<div class="detail-item"><small>${escapeHtml(key.replaceAll('_', ' '))}</small><strong>${formatted}</strong></div>`;
    }).join('');
    const relatedColumns = {
      items: [{key:'description',label:'Description'},{key:'quantity',label:'Quantity'},{key:'unit_price',label:'Unit price',format:'money'},{key:'line_total',label:'Total',format:'money'}],
      corrections: [{key:'event_id',label:'Correction ID'},{key:'event_kind',label:'Kind'},{key:'amount',label:'Amount',format:'money'},{key:'payment_id',label:'Original receipt'},{key:'reason',label:'Reason'},{key:'user_id',label:'Actor'},{key:'recorded_at',label:'Recorded UTC'}],
      payments: [{key:'payment_id',label:'Receipt ID'},{key:'recorded_at',label:'Recorded'},{key:'recorded_timezone',label:'Time basis'},{key:'payment_method',label:'Method'},{key:'reference',label:'Reference'},{key:'amount',label:'Amount',format:'money'}],
      doctors: [{ key: 'doctor_name', label: 'Doctor' }, { key: 'specialization', label: 'Specialization' }, { key: 'department_name', label: 'Department' }],
      appointments: [{ key: 'appointment_date', label: 'Date', format: 'date' }, { key: 'appointment_time', label: 'Time' }, { key: 'patient_name', label: 'Patient' }, { key: 'doctor_name', label: 'Doctor' }, { key: 'status', label: 'Status', format: 'status' }],
      prescriptions: [{ key: 'prescription_date', label: 'Date', format: 'date' }, { key: 'patient_name', label: 'Patient' }, { key: 'doctor_name', label: 'Doctor' }, { key: 'medicine_name', label: 'Medicine' }, { key: 'dosage', label: 'Dosage' }],
      admissions: [{ key: 'patient_name', label: 'Patient' }, { key: 'room_number', label: 'Room' }, { key: 'admission_date', label: 'Admitted', format: 'date' }, { key: 'discharge_date', label: 'Discharged', format: 'date' }],
      room_assignments: [{key:'admission_id',label:'Admission'},{key:'patient_name',label:'Patient'}, { key: 'room_number', label: 'Room' }, { key: 'started_at', label: 'Recorded start' }, { key: 'ended_at', label: 'Recorded end' }, { key: 'is_active', label: 'Active' }, { key: 'source', label: 'Source' }],
    };
    const sections = Object.entries(related).map(([name, rows]) => `
      <section class="detail-section" data-detail-section="${escapeHtml(name)}"><div class="detail-section-header"><h3>${escapeHtml(name.replaceAll('_', ' '))}</h3><span class="field-hint">${rows.length} records${name === 'room_assignments' ? ' · legacy timestamps may be unknown' : ''}</span></div>
      ${renderSimpleTable(rows, relatedColumns[name] || Object.keys(rows[0] || {}).slice(0, 5).map((key) => ({ key, label: key.replaceAll('_', ' ') })), `No related ${name} found.`)}</section>`).join('');
    let recordTitle;
    if (view === 'bills') {
      recordTitle = `Bill #${String(record.bill_id || recordId).padStart(4, '0')}${record.patient_name ? ` · ${record.patient_name}` : ''}`;
    } else if (view === 'prescriptions') {
      recordTitle = `Prescription #${String(record.prescription_id || recordId).padStart(4, '0')}${record.patient_name ? ` · ${record.patient_name}` : ''}`;
    } else if (view === 'admissions') {
      recordTitle = `Admission #${String(record.admission_id || recordId).padStart(4, '0')}${record.patient_name ? ` · ${record.patient_name}` : ''}`;
    } else if (view === 'appointments') {
      recordTitle = `Appointment #${String(record.appointment_id || recordId).padStart(4, '0')}${record.patient_name ? ` · ${record.patient_name}` : ''}`;
    } else {
      recordTitle = record[config.columns[0].key] ?? `${config.singular} #${recordId}`;
    }
    const print = view === 'bills' ? '<button class="button button-primary" type="button" data-action="print-bill">Print bill</button>' : '';
    const ledger = view === 'bills' ? `<button class="button button-secondary" type="button" data-action="open-ledger" data-id="${escapeHtml(recordId)}">Items and payments</button>` : '';
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card modal-wide bill-printable" role="dialog" aria-modal="true" aria-labelledby="recordDetailsTitle"><header class="modal-header"><div><h2 id="recordDetailsTitle">${escapeHtml(config.singular[0].toUpperCase() + config.singular.slice(1))} details</h2><p>Record values returned by the database-backed API. All monetary amounts are INR.</p></div><div class="print-actions">${view === 'bills' ? '<button class="button button-primary button-small" type="button" data-action="print-bill">Print bill</button>' : ''}<button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></div></header>
      <div class="modal-body"><article class="detail-card"><h3>${escapeHtml(recordTitle)}</h3><div class="detail-grid">${fields}</div>${view === 'bills' ? '<p>Legacy status is historical and is not a payment receipt. Only the payment history below records receipts. Reasoned manager corrections and linked refunds are separate retained events below. Net invoice totals include these corrections; original receipts remain unchanged.</p>' : ''}</article>${sections}<footer class="modal-footer">${ledger}${print}<button class="button button-secondary" type="button" data-action="close-modal">Close</button></footer></div></section></div>`;
    focusModal();
  }).catch((error) => {
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-label="Record details"><header class="modal-header"><h2>Record details</h2><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header><div class="error-state"><strong>Details could not be loaded</strong><p>${escapeHtml(error.message)}</p></div></section></div>`;
    focusModal();
  });
}

function pendingPaymentKey(billId) { return `hms.pending.payment.v1.${window.hmsUser?.user_id || 'legacy'}.${billId}`; }
function readPendingPayment(billId) {
  if (window.hmsUser && localStorage.getItem(`hms.pending.payment.v1.${billId}`)) throw new Error('An unowned pending payment from the pre-login version exists. Stop and ask a manager to reconcile the original key against the ledger; do not create a new payment or discard an uncertain request.');
  const text = localStorage.getItem(pendingPaymentKey(billId));
  return text ? JSON.parse(text) : null;
}
function restorePendingPayment(billId) {
  const pending = readPendingPayment(billId), form = document.getElementById('billPaymentForm');
  if (!pending || !form) return;
  for (const [name,value] of Object.entries(pending)) {
    const field = form.elements.namedItem(name); if (!field) continue;
    field.value = value ?? ''; if(field.tagName === 'SELECT') field.disabled=true; else field.readOnly=true;
  }
  form.querySelector('button[type="submit"]').textContent='Retry original payment';
  form.insertAdjacentHTML('afterbegin','<p role="status">Unresolved payment: retry the original request to recover its receipt. Details remain locked across close/reload; do not create another payment elsewhere.</p>');
}
async function openLedger(billId) {
  try {
    const data = await apiRequest(`/api/bills/${encodeURIComponent(billId)}/ledger`);
    const pending = readPendingPayment(billId);
    const canBill = !window.hmsUser || ['manager','cashier'].includes(window.hmsUser.role);
    const items = data.items.map((item) => `<tr><td>${escapeHtml(item.description)}</td><td>${escapeHtml(item.quantity)}</td><td>${escapeHtml(formatMoney(item.unit_price))}</td><td>${escapeHtml(formatMoney(item.line_total))}</td><td>${canBill && !data.charges_locked && moneyCents(data.paid) === 0n ? `<button type="button" data-action="edit-bill-item" data-id="${escapeHtml(item.item_id)}" data-description="${escapeHtml(item.description)}" data-quantity="${escapeHtml(item.quantity)}" data-price="${escapeHtml(item.unit_price)}">Edit</button> <button type="button" data-action="delete-bill-item" data-bill="${escapeHtml(billId)}" data-id="${escapeHtml(item.item_id)}">Remove</button>` : ''}</td></tr>`).join('');
    const correctionRows=(data.corrections||[]).map(e=>`<tr><td>#${escapeHtml(e.event_id)}</td><td>${escapeHtml(e.event_kind)}</td><td>${escapeHtml(formatMoney(e.amount))}</td><td>${escapeHtml(e.reason)}</td><td>${escapeHtml(e.recorded_at)} UTC</td><td>${escapeHtml(e.payment_id||'—')}</td></tr>`).join('');
    const payments = data.payments.map((p) => `<tr><td>${escapeHtml(p.recorded_at)} (${escapeHtml(p.recorded_timezone || 'legacy basis unknown')})</td><td>${escapeHtml(p.payment_method)}</td><td>${escapeHtml(p.reference || '—')}</td><td>${escapeHtml(formatMoney(p.amount))}</td></tr>`).join('');
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card modal-wide" role="dialog" aria-modal="true" aria-labelledby="ledgerTitle"><header class="modal-header"><div><h2 id="ledgerTitle">Bill #${escapeHtml(billId)} items and payments</h2><p>Legacy charge basis ${escapeHtml(formatMoney(data.legacy_charge_total))}; old status ${escapeHtml(data.legacy_status)} is not a payment record.</p></div><button class="icon-button" type="button" data-action="close-modal" aria-label="Close">×</button></header><div class="modal-body"><p><strong>Billed ${escapeHtml(formatMoney(data.billed))} · Paid ${escapeHtml(formatMoney(data.paid))} · Outstanding ${escapeHtml(formatMoney(data.balance))} · ${escapeHtml(data.status)}</strong></p><div id="formError" class="form-error" role="alert" hidden></div><h3>Additional invoice items</h3><div class="table-scroll"><table><thead><tr><th>Description</th><th>Quantity</th><th>Unit price</th><th>Total</th><th></th></tr></thead><tbody>${items || '<tr><td colspan="5">No additional items.</td></tr>'}</tbody></table></div>${canBill && !data.charges_locked && moneyCents(data.paid) === 0n ? `<form id="billItemForm" data-id="${escapeHtml(billId)}"><div class="form-grid"><div class="form-field"><label for="itemDescription">Description</label><input class="form-control" id="itemDescription" name="description" maxlength="200" required></div><div class="form-field"><label for="itemQuantity">Quantity</label><input class="form-control" id="itemQuantity" name="quantity" type="number" min="1" max="100000" step="1" required></div><div class="form-field"><label for="itemPrice">Unit price</label><input class="form-control" id="itemPrice" name="unit_price" type="number" min="0" step="0.01" required></div></div><button class="button button-primary" type="submit">Add item</button></form>` : '<p>Charges are locked after a payment is recorded.</p>'}<p>Managers authorize credits, refunds and financial write-offs in their personal workspace. Receipts and correction history are retained. A legacy Paid label is not a receipt.</p><h3>Corrective event history</h3><div class="table-scroll"><table><thead><tr><th>Event</th><th>Kind</th><th>Amount</th><th>Reason</th><th>Recorded</th><th>Original receipt</th></tr></thead><tbody>${correctionRows || '<tr><td colspan="6">No corrective events.</td></tr>'}</tbody></table></div><h3>Original payment history (gross receipts)</h3><div class="table-scroll"><table><thead><tr><th>Recorded</th><th>Method</th><th>Reference</th><th>Amount</th></tr></thead><tbody>${payments || '<tr><td colspan="4">No recorded payments.</td></tr>'}</tbody></table></div>${canBill && (moneyCents(data.balance) > 0n || pending) ? `<form id="billPaymentForm" data-id="${escapeHtml(billId)}"><input type="hidden" name="idempotency_key" value="${escapeHtml(pending?.idempotency_key || crypto.randomUUID())}"><div class="form-grid"><div class="form-field"><label for="paymentAmount">Amount</label><input class="form-control" id="paymentAmount" name="amount" type="number" min="0.01" ${pending ? '' : `max="${escapeHtml(data.balance)}"`} step="0.01" required></div><div class="form-field"><label for="paymentMethod">Method</label><select class="form-control" id="paymentMethod" name="payment_method"><option>Cash</option><option>Card</option><option>Transfer</option><option>Other</option></select></div><div class="form-field"><label for="paymentReference">Reference (optional)</label><input class="form-control" id="paymentReference" name="reference" maxlength="100"></div></div><button class="button button-primary" type="submit">Record payment</button></form>` : ''}</div></section></div>`;
    restorePendingPayment(billId);
    focusModal();
    return true;
  } catch (error) { toast(error.message, 'error'); return false; }
}

async function submitLedgerForm(form) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  const billId = form.dataset.id;
  let payload = Object.fromEntries(new FormData(form).entries());
  try {
    const isPayment = form.id === 'billPaymentForm';
    if (isPayment) {
      payload = readPendingPayment(billId) || payload;
      localStorage.setItem(pendingPaymentKey(billId), JSON.stringify(payload));
      restorePendingPayment(billId);
    }
    const editing = form.id === 'billItemForm' && form.dataset.itemId;
    const path = `/api/bills/${encodeURIComponent(billId)}/${form.id === 'billItemForm' ? 'items' : 'payments'}${editing ? `/${encodeURIComponent(editing)}` : ''}`;
    await apiRequest(path, { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    if (isPayment) localStorage.removeItem(pendingPaymentKey(billId));
    if (await openLedger(billId)) toast('Record saved.');
    if (window.hmsUser && window.hmsRefreshWorkspace) await window.hmsRefreshWorkspace();
    else if (state.view === 'bills') await refreshModuleRows();
    else if (state.view === 'dashboard') await loadDashboard();
  } catch (error) { showFormError(error.message); button.disabled = false; }
}

function openStockAdjustment(medicineId) {
  modalReturnFocus = document.activeElement;
  const medicine = state.rows.find((item) => String(item.medicine_id) === String(medicineId));
  if (!medicine) return;
  modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="stockTitle"><header class="modal-header"><div><h2 id="stockTitle">Adjust medicine stock</h2><p>${escapeHtml(medicine.medicine_name)} · current balance ${escapeHtml(medicine.stock_quantity)}</p></div><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header><div class="modal-body"><div id="formError" class="form-error" role="alert" hidden></div><form id="stockForm" data-id="${escapeHtml(medicineId)}"><div class="form-grid"><div class="form-field"><label for="stockChange">Quantity change</label><input class="form-control" id="stockChange" name="change" type="number" step="1" min="1" required placeholder="Enter units"></div><div class="form-field"><label for="stockDirection">Action</label><select class="form-control" id="stockDirection" name="stockDirection"><option value="add">Add stock</option><option value="remove">Remove stock</option></select></div><div class="form-field full-width"><small class="field-hint">Adjustments are atomic; the database guards prevent a balance below zero. This adjustment is not a dispensing record, and prescription creation never changes stock.</small></div></div><footer class="modal-footer"><button class="button button-secondary" type="button" data-action="close-modal">Cancel</button><button class="button button-primary" type="submit">Save adjustment</button></footer></form></div></section></div>`;
  document.getElementById('stockChange').focus();
}

function openDischarge(admissionId) {
  modalReturnFocus = document.activeElement;
  const row = state.rows.find((item) => String(item.admission_id) === String(admissionId));
  modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="dischargeTitle"><header class="modal-header"><div><h2 id="dischargeTitle">Discharge patient</h2><p>${escapeHtml(row?.patient_name || 'Patient')} · room ${escapeHtml(row?.room_number || '')}</p></div><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header><div class="modal-body"><div id="formError" class="form-error" role="alert" hidden></div><form id="dischargeForm" data-id="${escapeHtml(admissionId)}"><div class="form-field"><label for="dischargeDate">Discharge date <span class="required-mark" aria-hidden="true">*</span></label><input class="form-control" id="dischargeDate" name="discharge_date" type="date" min="${escapeHtml(row?.admission_date || '')}" max="${todayLocal()}" value="${todayLocal()}" required><small class="field-hint">The admission workflow releases this room in the same transaction.</small></div><footer class="modal-footer"><button class="button button-secondary" type="button" data-action="close-modal">Cancel</button><button class="button button-primary" type="submit">Confirm discharge</button></footer></form></div></section></div>`;
  document.getElementById('dischargeDate').focus();
}

async function openMoveRoom(admissionId) {
  modalReturnFocus = document.activeElement;
  const row = state.rows.find((item) => String(item.admission_id) === String(admissionId));
  try {
    const options = await loadOptions(true);
    const availableRooms = options.available_rooms || [];
    const roomChoices = availableRooms.map((room) => `<option value="${escapeHtml(room.id)}">${escapeHtml(room.label)}${room.room_type ? ` · ${escapeHtml(room.room_type)}` : ''}</option>`).join('');
    const roomControl = availableRooms.length
      ? `<select class="form-control" id="moveRoomSelect" name="room_id" required><option value="">Select an available room…</option>${roomChoices}</select>`
      : '<div class="empty-state"><strong>No rooms available</strong><span>Discharge or free a room before moving this patient.</span></div>';
    modalRoot.innerHTML = `<div class="modal-backdrop" data-action="backdrop-close"><section class="modal-card" role="dialog" aria-modal="true" aria-labelledby="moveRoomTitle"><header class="modal-header"><div><h2 id="moveRoomTitle">Move patient to another room</h2><p>${escapeHtml(row?.patient_name || 'Patient')} · currently in ${escapeHtml(row?.room_number || 'unknown room')}</p></div><button class="icon-button" type="button" aria-label="Close dialog" data-action="close-modal">×</button></header><div class="modal-body"><div id="formError" class="form-error" role="alert" hidden></div><form id="moveRoomForm" data-id="${escapeHtml(admissionId)}"><div class="form-field">${availableRooms.length ? '<label for="moveRoomSelect">Available room <span class="required-mark" aria-hidden="true">*</span></label>' : ''}${roomControl}<small class="field-hint">The active stay remains open; the admission workflow moves room occupancy in the same transaction.</small></div><footer class="modal-footer"><button class="button button-secondary" type="button" data-action="close-modal">Cancel</button>${availableRooms.length ? '<button class="button button-primary" type="submit">Move patient</button>' : ''}</footer></form></div></section></div>`;
    if (availableRooms.length) document.getElementById('moveRoomSelect').focus();
    else focusModal();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function focusModal() {
  const dialog = modalRoot.querySelector('[role="dialog"]');
  if (!dialog) return;
  const target = dialog.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])');
  if (target) {
    target.focus();
    return;
  }
  dialog.setAttribute('tabindex', '-1');
  dialog.focus();
}

function closeModal() {
  modalRoot.innerHTML = '';
  if (modalReturnFocus && modalReturnFocus.isConnected) modalReturnFocus.focus();
  modalReturnFocus = null;
}

function focusCurrentViewHeading() {
  const heading = mainContent.querySelector('.page-heading h2');
  if (heading) {
    heading.setAttribute('tabindex', '-1');
    heading.focus();
  } else {
    mainContent.focus();
  }
}

function focusRenderedRows(containerId = 'moduleTable', preferredSelector = '') {
  const container = document.getElementById(containerId);
  if (!container) return;
  const target = (preferredSelector ? container.querySelector(preferredSelector) : null)
    || container.querySelector('.table-wrap')
    || container.querySelector('.error-state button')
    || container;
  if (target === container) target.setAttribute('tabindex', '-1');
  target.focus();
}

function showFormError(message) {
  const el = document.getElementById('formError');
  if (!el) {
    toast(message, 'error');
    return;
  }
  el.textContent = message;
  el.hidden = false;
}

async function submitRecordForm(form) {
  const view = form.dataset.module;
  const config = MODULES[view];
  const payload = {};
  config.fields.forEach((field) => {
    const control = form.elements.namedItem(field.key);
    if (control && !control.disabled) payload[field.key] = control.value === '' ? null : control.value;
  });
  const id = form.dataset.id;
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await apiRequest(id ? `/api/${config.endpoint}/${id}` : `/api/${config.endpoint}`, {
      method: id ? 'PUT' : 'POST', body: JSON.stringify(payload),
    });
    closeModal();
    mainContent.focus();
    state.options = null;
    state.page = 1;
    toast(`${config.singular[0].toUpperCase()}${config.singular.slice(1)} ${id ? 'updated' : 'created'} successfully.`);
    if (state.view === 'dashboard') await loadDashboard();
    else {
      await loadModule();
      focusCurrentViewHeading();
    }
    await checkConnection();
  } catch (error) {
    showFormError(error.message);
    button.disabled = false;
    button.textContent = id ? 'Save changes' : 'Create record';
  }
}

async function changeAppointmentStatus(id, status) {
  const prompts = {
    'Checked In': 'Check this patient in for today’s appointment?',
    Waiting: 'Move this patient to the waiting queue?',
    'In Consultation': 'Start the consultation for this patient?',
    Completed: 'Mark the in-consultation visit as completed?',
    Cancelled: 'Cancel this scheduled appointment? The slot will be released for reuse.',
    'No-show': 'Mark this past appointment as No-show? Its slot will be released.',
  };
  if (!window.confirm(prompts[status] || `Change appointment status to ${status}?`)) return;
  try {
    await apiRequest(`/api/appointments/${id}`, { method: 'PUT', body: JSON.stringify({ status }) });
    const messages = {
      'Checked In': 'Patient checked in.',
      Waiting: 'Patient added to the waiting queue.',
      'In Consultation': 'Consultation started.',
      Completed: 'Visit marked completed; its slot is available.',
      Cancelled: 'Appointment cancelled; its slot is available.',
      'No-show': 'Appointment marked No-show; its slot is available.',
    };
    toast(messages[status] || 'Appointment status updated.');
    state.page = 1;
    await refreshModuleRows();
    focusRenderedRows();
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function deleteRecord(id) {
  const config = MODULES[state.view];
  const row = state.rows.find((item) => String(item[primaryKey(state.view)]) === String(id));
  const label = row?.[config.columns[0].key] || config.singular;
  if (!window.confirm(`Delete this ${config.singular} record${label ? ` (${label})` : ''}? Related records are protected by database foreign keys.`)) return;
  try {
    await apiRequest(`/api/${config.endpoint}/${id}`, { method: 'DELETE' });
    toast(`${config.singular[0].toUpperCase()}${config.singular.slice(1)} deleted.`);
    state.options = null;
    state.page = 1;
    await loadModule();
    focusCurrentViewHeading();
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function handleStockForm(form) {
  const amount = Number(form.elements.namedItem('change').value);
  const change = form.elements.namedItem('stockDirection').value === 'remove' ? -amount : amount;
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  button.textContent = 'Saving…';
  try {
    await apiRequest(`/api/medicines/${form.dataset.id}/stock-adjustments`, { method: 'POST', body: JSON.stringify({ change }) });
    closeModal();
    mainContent.focus();
    toast('Medicine stock updated.');
    await loadModule();
    focusCurrentViewHeading();
  } catch (error) {
    showFormError(error.message);
    button.disabled = false;
    button.textContent = 'Save adjustment';
  }
}

async function handleDischargeForm(form) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  button.textContent = 'Discharging…';
  try {
    await apiRequest(`/api/admissions/${form.dataset.id}/discharge`, {
      method: 'POST', body: JSON.stringify({ discharge_date: form.elements.namedItem('discharge_date').value }),
    });
    closeModal();
    mainContent.focus();
    toast('Patient discharged and room released.');
    state.options = null;
    await loadModule();
    focusCurrentViewHeading();
  } catch (error) {
    showFormError(error.message);
    button.disabled = false;
    button.textContent = 'Confirm discharge';
  }
}

async function handleMoveRoomForm(form) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  button.textContent = 'Moving…';
  try {
    await apiRequest(`/api/admissions/${form.dataset.id}`, {
      method: 'PUT', body: JSON.stringify({ room_id: form.elements.namedItem('room_id').value }),
    });
    closeModal();
    mainContent.focus();
    toast('Patient moved; room occupancy updated.');
    state.options = null;
    await loadModule();
    focusCurrentViewHeading();
  } catch (error) {
    showFormError(error.message);
    button.disabled = false;
    button.textContent = 'Move patient';
  }
}

function refreshConnectionDate() {
  const date = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', timeZone:hospitalZone }).format(new Date());
  document.getElementById('currentDate').textContent = date;
}

// Event delegation keeps controls functional after rendering fresh API responses.
document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-action]');
  if (!target) return;
  const action = target.dataset.action;
  if (action === 'navigate') {
    event.preventDefault();
    navigate(target.dataset.view);
  } else if (action === 'toggle-nav') {
    setMobileNavigation(!document.getElementById('sidebar').classList.contains('open'));
  } else if (action === 'close-nav') {
    setMobileNavigation(false);
  } else if (action === 'retry') {
    if (state.view === 'dashboard') loadDashboard();
    else if (state.view === 'reports') loadReports();
    else loadModule();
    checkConnection();
  } else if (action === 'add') {
    openForm(state.view);
  } else if (action === 'refresh') {
    await checkConnection();
    if (state.view === 'dashboard') loadDashboard();
    else if (state.view === 'reports') { state.options = null; loadReports(); }
    else { state.options = null; await loadOptions(true).catch(() => {}); refreshModuleRows(); }
  } else if (action === 'refresh-report') {
    state.reportPage = 1;
    refreshReportRows();
  } else if (action === 'export-report-csv') {
    exportReportCsv();
  } else if (action === 'open-appointment-queue') {
    state.appointmentView = 'queue';
    navigate('appointments');
  } else if (action === 'appointment-mode') {
    state.appointmentView = target.dataset.mode;
    state.page = 1;
    syncAppointmentControls();
    await refreshModuleRows();
    if (state.appointmentView !== 'queue') focusRenderedRows();
  } else if (action === 'page') {
    const page = Number(target.dataset.page);
    if (target.dataset.context === 'report') {
      state.reportPage = Math.max(1, page);
      await refreshReportRows();
      focusRenderedRows('reportTable');
    } else {
      state.page = Math.max(1, page);
      await refreshModuleRows();
      focusRenderedRows();
    }
  } else if (action === 'appointment-status') {
    changeAppointmentStatus(target.dataset.id, target.dataset.status);
  } else if (action === 'view-record') {
    openRecordDetails(target.dataset.view, target.dataset.id);
  } else if (action === 'print-bill' || action === 'print-patient') {
    window.print();
  } else if (action === 'sort') {
    const sort = target.dataset.sort;
    if (state.sort === sort) state.direction = state.direction === 'asc' ? 'desc' : 'asc';
    else { state.sort = sort; state.direction = 'asc'; }
    state.page = 1;
    await refreshModuleRows();
    const sortedButton = [...document.querySelectorAll('.sort-button')].find((button) => button.dataset.sort === sort);
    if (sortedButton) sortedButton.focus();
    else focusRenderedRows();
  } else if (action === 'edit') {
    const id = target.dataset.id;
    try {
      const record = await apiRequest(`/api/${MODULES[state.view].endpoint}/${id}`);
      openForm(state.view, record);
    } catch (error) { toast(error.message, 'error'); }
  } else if (action === 'delete') {
    deleteRecord(target.dataset.id);
  } else if (action === 'details') {
    openPatientHistory(target.dataset.id);
  } else if (action === 'open-ledger') {
    openLedger(target.dataset.id);
  } else if (action === 'edit-bill-item') {
    const form = document.getElementById('billItemForm');
    if (form) { form.dataset.itemId = target.dataset.id; form.elements.description.value = target.dataset.description; form.elements.quantity.value = target.dataset.quantity; form.elements.unit_price.value = target.dataset.price; form.querySelector('button[type=submit]').textContent = 'Save item'; form.elements.description.focus(); }
  } else if (action === 'delete-bill-item') {
    apiRequest(`/api/bills/${encodeURIComponent(target.dataset.bill)}/items/${encodeURIComponent(target.dataset.id)}`, { method: 'DELETE' }).then(() => openLedger(target.dataset.bill)).catch((error) => showFormError(error.message));
  } else if (action === 'stock') {
    openStockAdjustment(target.dataset.id);
  } else if (action === 'move-room') {
    openMoveRoom(target.dataset.id);
  } else if (action === 'discharge') {
    openDischarge(target.dataset.id);
  } else if (action === 'close-modal') {
    closeModal();
  } else if (action === 'backdrop-close' && event.target === target) {
    closeModal();
  }
});

document.addEventListener('input', (event) => {
  if (event.target.closest('#recordForm, #stockForm, #dischargeForm, #moveRoomForm')) {
    const errorEl = document.getElementById('formError');
    if (errorEl && !errorEl.hidden) {
      errorEl.hidden = true;
      errorEl.textContent = '';
    }
  }
  if (event.target.matches('.related-search')) {
    const select = document.getElementById(event.target.dataset.relatedSearch);
    const query = event.target.value.trim().toLocaleLowerCase();
    if (select) [...select.options].forEach((option, index) => {
      const hide = index > 0 && !option.textContent.toLocaleLowerCase().includes(query);
      option.hidden = hide;
      option.style.display = hide ? 'none' : '';
    });
  }
  if (event.target.id === 'moduleSearch') {
    if (state.view === 'appointments' && state.appointmentView === 'queue' && state.queueData) {
      const container = document.getElementById('moduleTable');
      if (container) {
        container.innerHTML = renderAppointmentQueue(state.queueData, MODULES.appointments);
      }
      return;
    }
    state.page = 1;
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(refreshModuleRows, 250);
  }
  if (event.target.closest('#recordForm') && state.view === 'bills') {
    const form = event.target.closest('#recordForm');
    const values = ['consultation_charge', 'room_charge', 'medicine_charge'].map((key) => form.elements.namedItem(key)?.value || '0');
    const preview = document.getElementById('billTotalPreview');
    if (preview) preview.textContent = formatMoney(sumMoney(values));
  }
});

document.addEventListener('change', async (event) => {
  if (event.target.matches('[data-action="page-size"]')) {
    state.pageSize = Number(event.target.value) || 25;
    if (event.target.dataset.context === 'report') {
      state.reportPage = 1;
      await refreshReportRows();
      focusRenderedRows('reportTable', '.page-size-select');
    } else {
      state.page = 1;
      await refreshModuleRows();
      focusRenderedRows('moduleTable', '.page-size-select');
    }
  } else if (event.target.id === 'reportSelect') {
    state.reportId = event.target.value;
    state.reportPage = 1;
    const config = REPORTS[state.reportId];
    document.getElementById('reportTitle').textContent = config.title;
    document.getElementById('reportDescription').textContent = config.description;
    const options = await loadOptions();
    document.getElementById('reportFilters').innerHTML = config.filters.map((key) => renderReportFilter(key, options)).join('');
    refreshReportRows();
  } else if (event.target.id === 'queueDate') {
    state.page = 1;
    refreshModuleRows();
  } else if (event.target.classList.contains('module-filter')) {
    state.page = 1;
    refreshModuleRows();
  } else if (event.target.classList.contains('report-filter')) {
    state.reportPage = 1;
    refreshReportRows();
  }
});

document.addEventListener('reset', (event) => {
  if (event.target.id !== 'recordForm') return;
  const errorEl = document.getElementById('formError');
  if (errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = '';
  }
  window.setTimeout(() => {
    event.target.querySelectorAll('.related-search').forEach((input) => {
      input.value = '';
      const select = document.getElementById(input.dataset.relatedSearch);
      if (select) [...select.options].forEach((option) => {
        option.hidden = false;
        option.style.display = '';
      });
    });
    const preview = document.getElementById('billTotalPreview');
    if (preview) {
      const form = event.target;
      const total = ['consultation_charge', 'room_charge', 'medicine_charge']
        .map((key) => form.elements.namedItem(key)?.value || '0');
      preview.textContent = formatMoney(sumMoney(total));
    }
  }, 0);
});

document.addEventListener('submit', (event) => {
  const form = event.target;
  if (form.id === 'billItemForm' || form.id === 'billPaymentForm') {
    event.preventDefault();
    submitLedgerForm(form);
  } else if (form.id === 'recordForm') {
    event.preventDefault();
    submitRecordForm(form);
  } else if (form.id === 'stockForm') {
    event.preventDefault();
    handleStockForm(form);
  } else if (form.id === 'dischargeForm') {
    event.preventDefault();
    handleDischargeForm(form);
  } else if (form.id === 'moveRoomForm') {
    event.preventDefault();
    handleMoveRoomForm(form);
  }
});

document.addEventListener('keydown', (event) => {
  const dialog = modalRoot.querySelector('[role="dialog"]');
  if (event.key === 'Escape' && dialog) {
    closeModal();
    return;
  }
  const sidebar = document.getElementById('sidebar');
  if (event.key === 'Escape' && sidebar.classList.contains('open')) {
    setMobileNavigation(false);
    return;
  }
  if (!dialog && event.key === 'Tab' && sidebar.classList.contains('open')) {
    const focusable = [...sidebar.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    if (!focusable.length) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!sidebar.contains(document.activeElement)) {
      event.preventDefault();
      first.focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
    return;
  }
  if (!dialog) return;
  if (event.key === 'Tab') {
    const focusable = [...dialog.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])')]
      .filter((element) => !element.hidden && element.offsetParent !== null);
    if (!focusable.length) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!dialog.contains(document.activeElement)) {
      event.preventDefault();
      first.focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});

window.addEventListener('popstate', () => {
  const desired = location.hash.slice(1);
  navigate(NAV_ITEMS.some((item) => item.id === desired) ? desired : 'dashboard', false);
});
window.addEventListener('resize', syncNavigationBreakpoint, { passive: true });

function bootAdmin() {
  renderNavigation();syncNavigationBreakpoint();
  const initialView=location.hash.slice(1);
  navigate(NAV_ITEMS.some(item=>item.id===initialView)?initialView:'dashboard');
  checkConnection();loadHospitalConfig();
}
refreshConnectionDate();
if (window.HMS_ROLE_BOOT) window.HMS_ROLE_BOOT({bootAdmin,clear:()=>{state.rows=[];state.options=null;state.view='workspace';state.dashboardRequest++;state.moduleRequest++;state.reportRequest++;},invoice:id=>openRecordDetails('bills',id),ledger:openLedger,history:openPatientHistory,config:loadHospitalConfig,layout:syncNavigationBreakpoint,money:formatMoney,today:todayLocal});
else bootAdmin();
window.setInterval(refreshConnectionDate,60000);
