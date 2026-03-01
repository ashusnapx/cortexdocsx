import * as React from "react";
import { cn } from "@/lib/utils";

interface SliderProps {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onValueChange: (next: number) => void;
  disabled?: boolean;
  className?: string;
}

export function Slider({
  value,
  min = 0,
  max = 1,
  step = 0.01,
  onValueChange,
  disabled,
  className,
}: SliderProps) {
  return (
    <input
      type='range'
      value={value}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      onChange={(event) => onValueChange(Number(event.target.value))}
      className={cn("slider h-2 w-full cursor-pointer appearance-none bg-transparent", className)}
    />
  );
}
