We want to host multiple cofy clouds on a single server.

It should be able to specify their configuration and settings in file format (eg YAML) instead of directly in python code.

We should have an overarching management api that allows admins of a cofy cloud to update their configuraton. (Which should trigger their cofy api to change their configuration accordingly)

This end user management API should have use an external identity provider (eg Keycloak) for authentication and authorization.

There should be a seprate level of management for the server admin to manage the overall server and the hosted cofy clouds.
This level should have an api that allows the server admin to create, update, and delete cofy clouds, as well as manage their configurations. They have more configuration options, such as allowed modules and sources.

A core piece of cofy cloud is still its custimibility. So it should be easy to create new modules our sources in the code, that fit specific needs for specific users, and have those only available to the cofy clouds that need them. The server admin should be able to manage which modules and sources are available to which cofy clouds.

Step one would be to be able to define a cofy cloud as a statefull config.