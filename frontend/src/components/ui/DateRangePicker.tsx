'use client';

import { useState } from 'react';

interface DateRangePickerProps {
  onDateChange: (range: { start_date?: string; end_date?: string }) => void;
  startDate?: string;
  endDate?: string;
}

export function DateRangePicker({ onDateChange, startDate, endDate }: DateRangePickerProps) {
  const [start, setStart] = useState(startDate || '');
  const [end, setEnd] = useState(endDate || '');

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setStart(value);
    onDateChange({ start_date: value || undefined, end_date: end || undefined });
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEnd(value);
    onDateChange({ start_date: start || undefined, end_date: value || undefined });
  };

  const handleClear = () => {
    setStart('');
    setEnd('');
    onDateChange({});
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 flex items-center gap-4">
      <label className="text-sm font-medium text-gray-700">Date Range:</label>
      <input
        type="date"
        value={start}
        onChange={handleStartChange}
        className="border border-gray-300 rounded px-3 py-2 text-sm"
      />
      <span className="text-gray-500">to</span>
      <input
        type="date"
        value={end}
        onChange={handleEndChange}
        min={start}
        className="border border-gray-300 rounded px-3 py-2 text-sm"
      />
      <button
        onClick={handleClear}
        className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
      >
        Clear
      </button>
    </div>
  );
}
