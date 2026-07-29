"use client";
import { QRCodeSVG } from "qrcode.react";

/**
 * On-theme QR code (gold on translucent card). Encodes any URL — used to point
 * judges at the GitHub repo from the closing slide.
 */
export function QrCode({
  value,
  size = 168,
  className = "",
}: {
  value: string;
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={`glass inline-flex items-center justify-center rounded-2xl border border-border p-4 shadow-2 ${className}`}
    >
      <QRCodeSVG
        value={value}
        size={size}
        bgColor="transparent"
        fgColor="#fca311"
        level="M"
        marginSize={0}
      />
    </div>
  );
}
