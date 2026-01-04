"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/channels", label: "Channels" },
  { href: "/videos", label: "Videos" },
  { href: "/clips", label: "Clips" },
  { href: "/posts", label: "Posts" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 border-r bg-background p-4">
      <div className="mb-6 text-lg font-semibold">Auto Clipper</div>
      <nav className="space-y-1">
        {nav.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "block rounded-md px-3 py-2 text-sm",
                active ? "bg-muted font-medium" : "hover:bg-muted/60",
              ].join(" ")}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
