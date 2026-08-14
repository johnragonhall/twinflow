"""The production `Network`, on its own import path.

    from twinflow.kernel.mqtt import MqttNetwork, TlsFiles, tls_context

Separate from `twinflow.kernel` because importing this module imports
`paho-mqtt`, which lives behind the `mqtt` extra. Re-exporting it from the
package would make every consumer of `Clock` resolve an MQTT client, and
doctrine D-10 puts heavy dependencies behind extras precisely so that a reader
who installs one brick gets one brick.

Boundary rule A1.1 makes everything under `twinflow.kernel._impl` private, so
this module is how a caller reaches the adapter without reaching into that
package. Installing without the extra leaves the import failing at `paho`,
which is the honest error: the dependency is genuinely absent.
"""

from __future__ import annotations

from twinflow.kernel._impl.real.mqtt import MqttNetwork, TlsFiles, tls_context

__all__ = ["MqttNetwork", "TlsFiles", "tls_context"]
