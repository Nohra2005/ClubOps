import { roleLabels, type Member } from '../api/types';

export default function Roster({
  members,
}: {
  members: Pick<Member, 'name' | 'email' | 'role'>[];
}) {
  return (
    <ul className="turnover-roster">
      {members.map((member) => (
        <li key={member.email}>
          <div>
            <strong>{member.name}</strong>
            <span>{member.email}</span>
          </div>
          <span>{roleLabels[member.role]}</span>
        </li>
      ))}
    </ul>
  );
}
