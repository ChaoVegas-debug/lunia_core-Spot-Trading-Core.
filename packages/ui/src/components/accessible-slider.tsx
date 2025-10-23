import * as React from 'react';

export const AccessibleSlider: React.FC<{
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
}> = ({ label, value, onChange, min, max, step = 1, disabled = false }) => {
  const id = React.useId();

  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-300 mb-2">
        {label}: {value}
      </label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        disabled={disabled}
        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
      />
    </div>
  );
};
