// calendariParrocchia -- parish group calendars with printable A4 sheets
// SPDX-License-Identifier: GPL-3.0-or-later
//
// "Are you sure?" on top of another dialog: deleting an event, closing one with
// unsaved changes. Esc and "cancel" mean no.
import { buttonClass, Dialog } from './Dialog'

type Props = {
  title: string
  text: string
  confirmLabel: string
  cancelLabel: string
  danger?: boolean
  busy?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog(props: Props) {
  return (
    <Dialog
      title={props.title}
      onClose={props.onCancel}
      footer={
        <>
          <button className={buttonClass.secondary} onClick={props.onCancel} autoFocus>
            {props.cancelLabel}
          </button>
          <button
            className={props.danger ? buttonClass.danger : buttonClass.primary}
            disabled={props.busy}
            onClick={props.onConfirm}
          >
            {props.confirmLabel}
          </button>
        </>
      }
    >
      <p className="text-ink-200">{props.text}</p>
      {props.error ? <p className="text-red-400">{props.error}</p> : null}
    </Dialog>
  )
}
