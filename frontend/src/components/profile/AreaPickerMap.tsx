interface AreaPickerMapProps {
  onClose: () => void
  onConfirm: () => void
}

export function AreaPickerMap({ onClose, onConfirm }: AreaPickerMapProps) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
      <div className="bg-surface border-4 border-black shadow-hard p-6 max-w-md w-full space-y-4">
        <h2 className="font-headline font-bold text-lg uppercase tracking-widest">Add Area</h2>
        <p className="font-body text-on-surface-variant text-sm">
          Area picker coming soon. You can subscribe to areas from the map view.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border-2 border-black font-headline font-bold text-sm uppercase tracking-widest"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-primary text-on-primary border-2 border-black font-headline font-bold text-sm uppercase tracking-widest"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
