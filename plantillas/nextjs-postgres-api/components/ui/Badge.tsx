type Color = "green" | "red" | "yellow" | "blue" | "gray";

const colors: Record<Color, string> = {
  green:  "bg-green-100 text-green-700",
  red:    "bg-red-100 text-red-700",
  yellow: "bg-yellow-100 text-yellow-700",
  blue:   "bg-blue-100 text-blue-700",
  gray:   "bg-gray-100 text-gray-600",
};

export function Badge({ label, color = "gray" }: { label: string; color?: Color }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[color]}`}>
      {label}
    </span>
  );
}
