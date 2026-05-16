💡 Strategic Check: The Hiver Transition
When you're ready to mesh Hiver, the first step in the k3s_vm repo will be creating the Vault Path for it.

You'll want to run:
kubectl exec -n vault vault-0 -- vault kv put secret/hiver-production idp_client_id="xyz" idp_client_secret="abc"

Once the secrets are in the vault, the Helm chart will just "sip" them through the External Secrets Operator, and Hiver will suddenly be able to accept your "Sovereign Passport."
