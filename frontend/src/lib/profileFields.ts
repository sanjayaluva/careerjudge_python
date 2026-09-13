/**
 * Role-specific profile field configuration (per SRS pages 8-22, plus the
 * Channel Partner / Corporate fields added for the accounts dossier gap).
 *
 * Shared by:
 *   - ProfilePage.tsx (self-service "Profile details" tab)
 *   - UsersPage.tsx (admin Add/Edit User form — D9 role-specific fields)
 * so both surfaces show the exact same fields for a given role.
 */
import type { UserProfile } from "@/api/types";
import type { RoleName } from "@/lib/constants";

export type FieldType = "text" | "select" | "textarea" | "date";

export interface ProfileFieldConfig {
  name: keyof UserProfile;
  label: string;
  type: FieldType;
  required?: boolean;
  options?: { value: string; label: string }[];
  max_length?: number;
}

// Common fields shown for ALL roles
export const COMMON_FIELDS: ProfileFieldConfig[] = [
  { name: "first_name", label: "First name", type: "text", max_length: 50 },
  { name: "middle_name", label: "Middle name", type: "text", max_length: 50 },
  { name: "last_name", label: "Last name", type: "text", max_length: 50 },
  {
    name: "gender",
    label: "Gender",
    type: "select",
    options: [
      { value: "", label: "Prefer not to say" },
      { value: "male", label: "Male" },
      { value: "female", label: "Female" },
      { value: "other", label: "Other" },
    ],
  },
  { name: "date_of_birth", label: "Date of birth", type: "date" },
  { name: "mobile", label: "Mobile number", type: "text", max_length: 15 },
  {
    name: "country_of_origin",
    label: "Country of origin",
    type: "text",
    max_length: 50,
    required: true,
  },
  { name: "state_province", label: "State / Province", type: "text", max_length: 50 },
  { name: "city", label: "City", type: "text", max_length: 100 },
  { name: "postal_code", label: "Postal code", type: "text", max_length: 20 },
  { name: "address_line1", label: "Address line 1", type: "text", max_length: 255 },
  { name: "address_line2", label: "Address line 2", type: "text", max_length: 255 },
];

// Individual user specific fields (SRS page 9-10)
export const INDIVIDUAL_FIELDS: ProfileFieldConfig[] = [
  {
    name: "occupation",
    label: "Occupation",
    type: "select",
    required: true,
    options: [
      { value: "", label: "Select..." },
      { value: "employed", label: "Employed" },
      { value: "self_employed", label: "Self Employed" },
      { value: "job_seeking_fresher", label: "Job seeking - Fresher" },
      { value: "job_seeking_non_fresher", label: "Job seeking - Non Fresher" },
      { value: "college_student", label: "College Student" },
      { value: "school_student", label: "School Student" },
    ],
  },
  { name: "current_position", label: "Current position", type: "text", max_length: 50 },
  {
    name: "highest_education",
    label: "Highest education",
    type: "text",
    max_length: 50,
    required: true,
  },
  { name: "work_experience", label: "Work experience (years)", type: "text", max_length: 2 },
  {
    name: "education_level",
    label: "Education level",
    type: "select",
    required: true,
    options: [
      { value: "", label: "Select..." },
      { value: "5-12", label: "5-12" },
      { value: "undergraduate", label: "Undergraduate" },
      { value: "post_graduate", label: "Post Graduate" },
      { value: "m_phil", label: "M-Phil" },
      { value: "phd", label: "PhD" },
    ],
  },
  { name: "institution_name", label: "Institution name", type: "text", max_length: 50 },
  { name: "place_of_institution", label: "Place of institution", type: "text", max_length: 50 },
  { name: "location", label: "Location", type: "text", max_length: 50 },
];

// Professional fields (Psychometrician/SME/Reviewer/Trainer/Counsellor, SRS pages 10-13)
export const PROFESSIONAL_FIELDS: ProfileFieldConfig[] = [
  {
    name: "occupation",
    label: "Occupation",
    type: "select",
    required: true,
    options: [
      { value: "", label: "Select..." },
      { value: "employed", label: "Employed" },
      { value: "self_employed", label: "Self Employed" },
      { value: "retired", label: "Retired" },
    ],
  },
  { name: "current_position", label: "Current position", type: "text", max_length: 50 },
  {
    name: "highest_education",
    label: "Highest education qualification",
    type: "text",
    max_length: 50,
    required: true,
  },
  {
    name: "work_experience",
    label: "Work experience (years)",
    type: "text",
    max_length: 2,
    required: true,
  },
  { name: "domain_experience", label: "Domain experience (years)", type: "text", max_length: 2 },
  { name: "pan_number", label: "PAN number", type: "text", max_length: 15, required: true },
  {
    name: "bank_account_number",
    label: "Bank account number",
    type: "text",
    max_length: 15,
    required: true,
  },
  { name: "bank_name", label: "Bank name", type: "text", max_length: 20, required: true },
  { name: "branch_name", label: "Branch name", type: "text", max_length: 25, required: true },
  { name: "ifsc_code", label: "IFSC code", type: "text", max_length: 15, required: true },
  {
    name: "contact_address",
    label: "Contact address",
    type: "textarea",
    max_length: 100,
    required: true,
  },
  {
    name: "permanent_address",
    label: "Permanent address",
    type: "textarea",
    max_length: 100,
    required: true,
  },
  { name: "bio", label: "User Bio", type: "textarea", max_length: 1000 },
];

// Channel Partner fields (SRS page 13 + dossier gap: agency_name/allocated_region)
export const CHANNEL_PARTNER_FIELDS: ProfileFieldConfig[] = [
  { name: "current_position", label: "Current position", type: "text", max_length: 50 },
  { name: "agency_name", label: "Agency name", type: "text", max_length: 100 },
  { name: "allocated_region", label: "Allocated region", type: "text", max_length: 100 },
  { name: "pan_number", label: "PAN number", type: "text", max_length: 15, required: true },
  {
    name: "bank_account_number",
    label: "Bank account number",
    type: "text",
    max_length: 15,
    required: true,
  },
  { name: "bank_name", label: "Bank name", type: "text", max_length: 20, required: true },
  { name: "branch_name", label: "Branch name", type: "text", max_length: 25, required: true },
  { name: "ifsc_code", label: "IFSC code", type: "text", max_length: 15, required: true },
  {
    name: "channel_partner_agreement_id",
    label: "Channel Partner Agreement ID",
    type: "text",
    max_length: 50,
  },
  {
    name: "contract_period",
    label: "Contract period (years)",
    type: "text",
    max_length: 2,
    required: true,
  },
];

// Corporate fields (corp_admin / corp_exclusive — dossier gap: manager_name/tan_number)
export const CORPORATE_FIELDS: ProfileFieldConfig[] = [
  { name: "current_position", label: "Current position", type: "text", max_length: 50 },
  { name: "manager_name", label: "Manager name", type: "text", max_length: 100 },
  { name: "pan_number", label: "PAN number", type: "text", max_length: 15 },
  { name: "tan_number", label: "TAN number", type: "text", max_length: 15 },
  { name: "bio", label: "User Bio", type: "textarea", max_length: 1000 },
];

/** Returns the role-specific fields to show based on the user's role. */
export function getRoleSpecificFields(role: RoleName | null): ProfileFieldConfig[] {
  switch (role) {
    case "individual":
      return INDIVIDUAL_FIELDS;
    case "psychometrician":
    case "sme":
    case "reviewer":
    case "trainer":
    case "counsellor":
      return PROFESSIONAL_FIELDS;
    case "channel_partner":
      return CHANNEL_PARTNER_FIELDS;
    case "corp_admin":
    case "corp_exclusive":
      return CORPORATE_FIELDS;
    default:
      return [];
  }
}
