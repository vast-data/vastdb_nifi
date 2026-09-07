## DropVastDBTable Processor

   * **Description:** Drops a specified table from a VastDB schema.
   * **Properties:**
     * **VastDB Endpoint:** The URL of your VastDB endpoint.
     * **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
     * **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `SSL Context Service`, `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
     * **SSL Context Service:** *(when **TLS Verification** is `SSL Context Service`)* An [SSLContextService](https://nifi.apache.org/components/org.apache.nifi.ssl.StandardSSLContextService/) supplying the truststore used to verify VastDB. See [TLS](./TLS.md).
     * **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
     * **VastDB Bucket:** The VastDB bucket containing your data.
     * **VastDB Database Schema:** The VastDB schema containing the table to drop.
     * **VastDB Table Name:** The name of the table to drop. This can be an Expression Language expression that references FlowFile attributes.