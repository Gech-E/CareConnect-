import { ChevronRight, Star, UserRound } from "lucide-react";
import type { Clinician } from "../../lib/api";

export const fullName = (doctor: Clinician) =>
  `Dr. ${doctor.first_name} ${doctor.last_name}`;

export function DoctorGrid({
  doctors,
  onSelect,
}: {
  doctors: Clinician[];
  onSelect: (doctor: Clinician) => void;
}) {
  if (!doctors.length)
    return (
      <div className="card empty">
        No clinicians found. Try another search or specialty.
      </div>
    );
  return (
    <div className="doctor-grid">
      {doctors.map((doctor) => (
        <button
          key={doctor.id}
          className="doctor-card card"
          onClick={() => onSelect(doctor)}
          aria-label={`View profile for ${fullName(doctor)}`}
        >
          <div className="avatar">
            <UserRound size={33} />
          </div>
          <h3>{fullName(doctor)}</h3>
          <span className="sub">
            {doctor.roles?.map((role) => role.specialty).join(" · ") ||
              "Healthcare professional"}
          </span>
          {(doctor.review_count ?? 0) > 0 && (
            <span className="rating">
              <Star size={15} fill="currentColor" /> {doctor.average_rating}
              <span className="sub">({doctor.review_count ?? 0} reviews)</span>
            </span>
          )}
          <span className="doctor-foot">
            <span className="sub">View profile</span>
            <ChevronRight color="#0a807c" size={19} />
          </span>
        </button>
      ))}
    </div>
  );
}
