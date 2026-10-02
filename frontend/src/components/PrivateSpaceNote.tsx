/**
 * Report 9 #39-#47: a small label on the Question Bank / Assessments /
 * Reports / Training screens telling the Corporate Exclusive Admin that he
 * works in his organization's private space. With several exclusive
 * organizations he picks the one new items are added to. Renders nothing for
 * every other role.
 */
import { usePrivateSpace } from "@/hooks/usePrivateSpace";

export function PrivateSpaceNote({ what }: { what: string }) {
  const { isPrivateAuthor, orgs, selectedOrgId, selectOrg } = usePrivateSpace();
  if (!isPrivateAuthor) return null;
  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-2 rounded-md border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-800"
    >
      <span>
        <strong>Your organization&apos;s private {what}</strong>
        {orgs.length === 1 ? ` — ${orgs[0].name}` : ""}. Only your organization can see it.
      </span>
      {orgs.length > 1 && (
        <label className="ml-auto flex items-center gap-2">
          <span className="text-xs">Add new items to</span>
          <select
            aria-label="Organization for new items"
            className="h-8 rounded-md border border-primary-200 bg-white px-2 text-sm"
            value={selectedOrgId ?? ""}
            onChange={(e) => selectOrg(Number(e.target.value))}
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
